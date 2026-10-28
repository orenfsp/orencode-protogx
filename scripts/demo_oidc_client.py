"""Fictional OIDC relying party on http://127.0.0.1:9012.

No client secret: this is a public authorization-code client with PKCE. State,
nonce, verifier and tokens stay in bounded, short-lived server memory. This demo
supports one local process, not production sessions or real third-party login.
"""

import base64
import hashlib
import html
import json
import os
import secrets
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

import requests
from jwcrypto import jwk, jwt
from jwcrypto.common import JWException

ISSUER = os.environ.get("FSP_OIDC_ISSUER", "http://127.0.0.1:8000").rstrip("/")
CLIENT_ID = os.environ.get("FSP_DEMO_CLIENT_ID", "fsp-fictional-client")
CALLBACK = "http://127.0.0.1:9012/callback"


def verify_id_token(raw, keys, nonce, client_id=CLIENT_ID, issuer=ISSUER):
    token = jwt.JWT(
        jwt=raw,
        key=jwk.JWKSet.from_json(json.dumps(keys)),
        algs=["RS256"],
        check_claims={"iss": issuer, "aud": client_id, "nonce": nonce, "exp": None},
    )
    claims = json.loads(token.claims)
    if (
        not isinstance(claims.get("exp"), int)
        or claims["exp"] <= time.time()
        or claims.get("iat", 0) > time.time() + 30
    ):
        raise ValueError("Token time validation failed")
    return claims


def main():
    sessions = {}
    parsed = urlsplit(ISSUER)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in ["127.0.0.1", "localhost"]
    ):
        raise ValueError("HTTPS issuer required outside loopback demo")
    metadata = requests.get(
        ISSUER + "/o/.well-known/openid-configuration", timeout=5
    ).json()
    if metadata.get("issuer") != ISSUER:
        raise ValueError("Issuer mismatch")
    # Pinned issuer, no untrusted discovery redirects or arbitrary endpoint hosts.
    for key in [
        "authorization_endpoint",
        "token_endpoint",
        "userinfo_endpoint",
        "jwks_uri",
    ]:
        if (
            urlsplit(metadata[key]).netloc != parsed.netloc
            or urlsplit(metadata[key]).scheme != parsed.scheme
        ):
            raise ValueError("Endpoint origin mismatch")

    class Handler(BaseHTTPRequestHandler):
        def page(self, text, *, cookie=None, status=200):
            content = (
                "<!doctype html><html lang='ru'><meta charset='utf-8'><title>Вымышленный партнёр</title><body><h1>Вымышленный региональный сервис</h1>"
                + text
                + "</body></html>"
            ).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(content)

        def get_session(self):
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            sid = cookies.get("fsp_demo_client")
            return sid.value if sid else ""

        def do_GET(self):
            route = urlsplit(self.path)
            if route.path == "/login":
                expired = [
                    sid
                    for sid, s in sessions.items()
                    if s["created"] < time.time() - 600
                ]
                for sid in expired:
                    sessions.pop(sid, None)
                if len(sessions) > 100:
                    return self.page("Демо занято; повторите позже", status=429)
                sid, state, nonce, verifier = [
                    secrets.token_urlsafe(32) for _ in range(4)
                ]
                challenge = (
                    base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                    .rstrip(b"=")
                    .decode()
                )
                sessions[sid] = {
                    "state": state,
                    "nonce": nonce,
                    "verifier": verifier,
                    "created": time.time(),
                }
                query = urlencode(
                    {
                        "client_id": CLIENT_ID,
                        "redirect_uri": CALLBACK,
                        "response_type": "code",
                        "scope": "openid profile fsp_roles fsp_disciplines fsp_rank",
                        "state": state,
                        "nonce": nonce,
                        "code_challenge": challenge,
                        "code_challenge_method": "S256",
                    }
                )
                self.send_response(302)
                self.send_header(
                    "Location", metadata["authorization_endpoint"] + "?" + query
                )
                self.send_header(
                    "Set-Cookie",
                    f"fsp_demo_client={sid}; HttpOnly; SameSite=Lax; Path=/",
                )
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            if route.path == "/callback":
                sid = self.get_session()
                session = sessions.get(sid)
                query = parse_qs(route.query)
                if (
                    not session
                    or session.get("used")
                    or session["created"] < time.time() - 600
                    or not secrets.compare_digest(
                        query.get("state", [""])[0], session["state"]
                    )
                    or query.get("iss", [ISSUER])[0] != ISSUER
                ):
                    return self.page("Ошибка проверки state или issuer", status=400)
                session["used"] = True
                if "error" in query:
                    return self.page("Передача данных отклонена", status=400)
                try:
                    response = requests.post(
                        metadata["token_endpoint"],
                        data={
                            "grant_type": "authorization_code",
                            "client_id": CLIENT_ID,
                            "redirect_uri": CALLBACK,
                            "code": query.get("code", [""])[0],
                            "code_verifier": session["verifier"],
                        },
                        timeout=5,
                        allow_redirects=False,
                    )
                    response.raise_for_status()
                    tokens = response.json()
                    keys = requests.get(
                        metadata["jwks_uri"], timeout=5, allow_redirects=False
                    ).json()
                    claims = verify_id_token(tokens["id_token"], keys, session["nonce"])
                    info_response = requests.get(
                        metadata["userinfo_endpoint"],
                        headers={"Authorization": "Bearer " + tokens["access_token"]},
                        timeout=5,
                        allow_redirects=False,
                    )
                    info_response.raise_for_status()
                    info = info_response.json()
                    if info.get("sub") != claims.get("sub"):
                        raise ValueError("Subject mismatch")
                    session["access_token"] = tokens["access_token"]
                    session["logout_csrf"] = secrets.token_urlsafe(32)
                    return self.page(
                        "<h2>Вход выполнен через ФСП ID</h2><pre>"
                        + html.escape(json.dumps(info, ensure_ascii=False, indent=2))
                        + "</pre><form method='post' action='/logout'><input type='hidden' name='csrf' value='"
                        + session["logout_csrf"]
                        + "'><button>Выйти из тестового клиента</button></form>"
                    )
                except (requests.RequestException, ValueError, KeyError, JWException):
                    sessions.pop(sid, None)
                    return self.page(
                        "Безопасная ошибка OIDC. Повторите вход.", status=400
                    )
            self.page(
                "<p>Фиктивный клиент: проверяет подпись, issuer, audience, nonce, срок и userinfo.</p><a href='/login'>Войти через ФСП ID</a>"
            )

        def do_POST(self):
            sid = self.get_session()
            session = sessions.get(sid)
            length = int(self.headers.get("Content-Length", 0))
            if (
                self.path != "/logout"
                or length > 4096
                or not session
                or not session.get("access_token")
            ):
                return self.page("Неверный запрос", status=400)
            data = parse_qs(self.rfile.read(length).decode())
            if not secrets.compare_digest(
                data.get("csrf", [""])[0], session.get("logout_csrf", "")
            ):
                return self.page("Ошибка CSRF", status=403)
            try:
                response = requests.post(
                    ISSUER + "/o/revoke_token/",
                    data={"client_id": CLIENT_ID, "token": session["access_token"]},
                    timeout=5,
                    allow_redirects=False,
                )
                response.raise_for_status()
            except requests.RequestException:
                return self.page(
                    "Не удалось подтвердить отзыв токена; повторите выход", status=503
                )
            sessions.pop(sid, None)
            self.page(
                "<h2>Вы вышли из тестового клиента</h2><p>Токен отозван. Сессия федерации управляется отдельно.</p><a href='/'>Начать снова</a>",
                cookie="fsp_demo_client=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/",
            )

        def log_message(self, *args):
            pass  # Never log authorization codes, callback query strings or tokens.

    HTTPServer(("127.0.0.1", 9012), Handler).serve_forever()


if __name__ == "__main__":
    main()
