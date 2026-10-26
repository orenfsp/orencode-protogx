"""Exercise the same-origin Phase 1 flow against a running Compose stack."""

import json
import secrets
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:3000"
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def call(path, method="GET", body=None, token=None):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers.update({"Content-Type": "application/json", "Origin": base})
    if token:
        headers["X-CSRFToken"] = token
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with opener.open(request, timeout=20) as response:
            data = response.read()
            return response.status, json.loads(data) if data else None
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def csrf():
    status, data = call("/api/v1/auth/csrf/")
    assert status == 200, (status, data)
    return data["csrfToken"]


email = f"smoke-{secrets.token_hex(6)}@example.test"
password = secrets.token_urlsafe(24) + "A1!"
status, registered = call(
    "/api/v1/auth/register/",
    "POST",
    {
        "email": email,
        "password": password,
        "full_name": "Фиктивный Тестовый Участник",
        "date_of_birth": "2000-01-01",
        "consent": True,
        "consent_version": "v1-demo-2026-10-27",
    },
    csrf(),
)
assert status == 201 and registered["user"]["active_role"] == "athlete", (status, registered)
assert call("/api/v1/auth/me/")[1]["email"] == email
status, _ = call("/api/v1/auth/active-role/", "POST", {"role": "judge"}, csrf())
assert status == 403, status
assert call("/api/v1/auth/logout/", "POST", {}, csrf())[0] == 204
status, logged_in = call("/api/v1/auth/login/", "POST", {"email": email, "password": password}, csrf())
assert status == 200 and logged_in["user"]["email"] == email, (status, logged_in)
assert len(call("/api/v1/disciplines/")[1]) == 6
assert call("/api/v1/health/")[1]["status"] == "ok"
print("PASS: registration, session login/logout, role denial, six disciplines, health")
