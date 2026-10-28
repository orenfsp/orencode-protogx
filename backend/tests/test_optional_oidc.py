import base64
import hashlib
import json
from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlsplit

from django.conf import settings
from django.test import Client, override_settings
from django.utils import timezone
from jwcrypto import jwk, jwt
from oauth2_provider.models import AccessToken, Application, Grant

from apps.extensions.models import OIDCClientPolicy, OIDCSharingConsent

from .optional_helpers import OptionalCase


class OIDCTests(OptionalCase):
    def test_minor_requires_separate_guardian_data_sharing_authorization(self):
        from datetime import date

        from apps.accounts.models import Guardian

        self.athlete.date_of_birth = date(2012, 1, 1)
        self.athlete.save(update_fields=["date_of_birth"])
        guardian = Guardian.objects.create(
            minor=self.athlete,
            full_name="Вымышленный представитель",
            relationship="родитель",
            confirmation_status="verified",
        )
        self.assertEqual(
            self.browser.get(
                "/o/authorize/?" + urlencode(self.parameters())
            ).status_code,
            403,
        )
        self.login(self.other, "athlete")
        payload = {
            "guardian": guardian.pk,
            "application": self.app.pk,
            "scopes": ["openid", "profile", "fsp_roles"],
            "text_version": "fictional-guardian-sharing-v1",
            "signed_evidence_url": "https://private.example.test/fictional-consent",
        }
        self.assertEqual(
            self.post("fsp-id/guardian-authorizations/", payload).status_code, 403
        )
        self.login(self.federation, "federation")
        authorized = self.post("fsp-id/guardian-authorizations/", payload)
        self.assertEqual(authorized.status_code, 201, authorized.data)
        tokens = self.exchange(self.authorize()).json()
        self.assertEqual(
            self.browser.get(
                "/o/userinfo/", HTTP_AUTHORIZATION="Bearer " + tokens["access_token"]
            ).status_code,
            200,
        )
        self.assertEqual(
            self.post(
                f"fsp-id/guardian-authorizations/{authorized.data['id']}/revoke/"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.browser.get(
                "/o/userinfo/", HTTP_AUTHORIZATION="Bearer " + tokens["access_token"]
            ).status_code,
            401,
        )

    def test_admin_manages_redirects_scopes_and_hashed_secret(self):
        from django.contrib.auth.hashers import check_password

        self.login(self.federation, "federation")
        payload = {
            "name": "Вымышленный конфиденциальный клиент",
            "client_type": "confidential",
            "redirect_uris": ["https://partner.example.test/callback"],
            "scopes": ["openid", "profile"],
        }
        created = self.post("fsp-id/clients/", payload)
        self.assertEqual(created.status_code, 201, created.data)
        app = Application.objects.get(pk=created.data["id"])
        self.assertTrue(
            check_password(created.data["client_secret"], app.client_secret)
        )
        rotated = self.post(f"fsp-id/clients/{app.pk}/rotate-secret/")
        self.assertEqual(rotated.status_code, 200, rotated.data)
        app.refresh_from_db()
        self.assertTrue(
            check_password(rotated.data["client_secret"], app.client_secret)
        )
        OIDCSharingConsent.objects.create(
            user=self.athlete, application=app, scopes=["openid", "profile"]
        )
        updated = self.client.put(
            f"/api/v1/fsp-id/clients/{app.pk}/",
            {**payload, "scopes": ["openid"]},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertFalse(
            OIDCSharingConsent.objects.filter(application=app, revoked_at=None).exists()
        )
        self.assertEqual(
            self.post(
                "fsp-id/clients/",
                {**payload, "redirect_uris": ["https://partner.example.test/*"]},
            ).status_code,
            400,
        )
        self.login(self.athlete, "athlete")
        self.assertEqual(
            self.post(f"fsp-id/clients/{app.pk}/rotate-secret/").status_code, 403
        )

    def test_confidential_code_requires_client_authentication(self):
        self.app.client_type = "confidential"
        self.app.client_secret = "fictional-confidential-secret"
        self.app.save()
        code = self.authorize()
        self.assertEqual(self.exchange(code).status_code, 401)
        response = self.browser.post(
            "/o/token/",
            {
                "client_id": self.app.client_id,
                "client_secret": "fictional-confidential-secret",
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "http://localhost:9012/callback",
                "code_verifier": self.verifier,
            },
        )
        self.assertEqual(response.status_code, 200, response.content)

    def setUp(self):
        super().setUp()
        self.key = jwk.JWK.generate(kty="RSA", size=2048)
        config = {
            **settings.OAUTH2_PROVIDER,
            "OIDC_ENABLED": True,
            "OIDC_RSA_PRIVATE_KEY": self.key.export_to_pem(
                private_key=True, password=None
            ).decode(),
            "OIDC_ISS_ENDPOINT": "http://testserver",
            "OIDC_USERINFO_ENDPOINT": "http://testserver/o/userinfo/",
            "ALWAYS_RELOAD_OAUTHLIB_CORE": True,
        }
        self.override = override_settings(
            FSP_OIDC_ENABLED=True,
            FSP_OIDC_ISSUER="http://testserver",
            OAUTH2_PROVIDER=config,
        )
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.browser = Client()
        self.browser.force_login(self.athlete)
        self.app = Application.objects.create(
            name="Вымышленный OIDC клиент",
            user=self.federation,
            client_type="public",
            authorization_grant_type="authorization-code",
            redirect_uris="http://localhost:9012/callback",
            algorithm="RS256",
        )
        OIDCClientPolicy.objects.create(
            application=self.app,
            scopes=["openid", "profile", "fsp_roles", "fsp_disciplines", "fsp_rank"],
        )
        self.verifier = "x" * 64
        self.challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )

    def parameters(self, scope="openid profile fsp_roles"):
        return {
            "client_id": self.app.client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:9012/callback",
            "scope": scope,
            "state": "fictional-state-123",
            "nonce": "fictional-nonce-123",
            "code_challenge": self.challenge,
            "code_challenge_method": "S256",
        }

    def authorize(self, scope="openid profile fsp_roles"):
        params = self.parameters(scope)
        response = self.browser.get("/o/authorize/?" + urlencode(params))
        self.assertEqual(response.status_code, 200, response.content[:500])
        fields = {
            field.name: field.value() or ""
            for field in response.context["form"]
            if field.is_hidden
        }
        response = self.browser.post("/o/authorize/", {**fields, "allow": "true"})
        self.assertEqual(response.status_code, 302, response.content[:500])
        query = parse_qs(urlsplit(response["Location"]).query)
        self.assertEqual(query["state"], [params["state"]])
        return query["code"][0]

    def exchange(self, code, verifier=None):
        return self.browser.post(
            "/o/token/",
            {
                "client_id": self.app.client_id,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "http://localhost:9012/callback",
                "code_verifier": verifier or self.verifier,
            },
        )

    def test_full_code_pkce_consent_jwks_userinfo_revoke(self):
        discovery = self.browser.get("/o/.well-known/openid-configuration")
        self.assertEqual(discovery.status_code, 200, discovery.content)
        self.assertEqual(discovery.json()["code_challenge_methods_supported"], ["S256"])
        code = self.authorize()
        response = self.exchange(code)
        self.assertEqual(response.status_code, 200, response.content)
        tokens = response.json()
        self.assertNotIn("refresh_token", tokens)
        keys = self.browser.get("/o/.well-known/jwks.json").json()
        verified = jwt.JWT(
            jwt=tokens["id_token"],
            key=jwk.JWKSet.from_json(json.dumps(keys)),
            check_claims={
                "iss": "http://testserver",
                "aud": self.app.client_id,
                "nonce": "fictional-nonce-123",
                "exp": None,
            },
        )
        claims = json.loads(verified.claims)
        self.assertEqual(claims["name"], self.athlete.full_name)
        self.assertLessEqual(claims["exp"] - claims["iat"], 300)
        self.assertEqual(AccessToken.objects.get().token, "")
        info = self.browser.get(
            "/o/userinfo/", HTTP_AUTHORIZATION="Bearer " + tokens["access_token"]
        )
        self.assertEqual(info.status_code, 200, info.content)
        self.assertEqual(info.json()["sub"], claims["sub"])
        self.assertNotIn("ranks", info.json())
        self.assertEqual(self.exchange(code).status_code, 400)
        revoked = self.browser.post(
            "/o/revoke_token/",
            {"client_id": self.app.client_id, "token": tokens["access_token"]},
        )
        self.assertEqual(revoked.status_code, 200, revoked.content)
        self.assertEqual(
            self.browser.get(
                "/o/userinfo/", HTTP_AUTHORIZATION="Bearer " + tokens["access_token"]
            ).status_code,
            401,
        )

    def test_pkce_wrong_redirect_nonce_missing_and_form_tampering(self):
        params = self.parameters()
        for key, value in [
            ("code_challenge_method", "plain"),
            ("nonce", ""),
            ("state", ""),
        ]:
            self.assertEqual(
                self.browser.get(
                    "/o/authorize/?" + urlencode({**params, key: value})
                ).status_code,
                400,
            )
        response = self.browser.get(
            "/o/authorize/?"
            + urlencode(
                {**params, "redirect_uri": "https://evil.example.test/callback"}
            )
        )
        self.assertNotEqual(response.status_code, 302)
        self.browser.get("/o/authorize/?" + urlencode(params))
        self.assertEqual(
            self.browser.post(
                "/o/authorize/",
                {**params, "scope": "openid profile fsp_rank", "allow": "true"},
            ).status_code,
            400,
        )
        code = self.authorize()
        self.assertEqual(self.exchange(code, "wrong" * 16).status_code, 400)

    def test_consent_revocation_expiry_and_disabled_client(self):
        tokens = self.exchange(self.authorize("openid")).json()
        info = self.browser.get(
            "/o/userinfo/", HTTP_AUTHORIZATION="Bearer " + tokens["access_token"]
        )
        self.assertEqual(list(info.json()), ["sub"])
        AccessToken.objects.update(expires=timezone.now() - timedelta(seconds=1))
        self.assertEqual(
            self.browser.get(
                "/o/userinfo/", HTTP_AUTHORIZATION="Bearer " + tokens["access_token"]
            ).status_code,
            401,
        )
        tokens = self.exchange(self.authorize()).json()
        self.login(self.athlete, "athlete")
        consent = OIDCSharingConsent.objects.filter(user=self.athlete).first()
        self.assertEqual(
            self.post(f"fsp-id/consents/{consent.pk}/revoke/").status_code, 200
        )
        self.assertEqual(
            self.browser.get(
                "/o/userinfo/", HTTP_AUTHORIZATION="Bearer " + tokens["access_token"]
            ).status_code,
            401,
        )
        self.login(self.federation, "federation")
        self.assertEqual(
            self.post(f"fsp-id/clients/{self.app.pk}/disable/").status_code, 200
        )
        self.assertEqual(Grant.objects.count(), 0)

    def test_browser_hidden_fields_require_csrf_and_key_rotation_keeps_old_jwks(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.athlete)
        response = browser.get("/o/authorize/?" + urlencode(self.parameters()))
        fields = {
            field.name: field.value() or ""
            for field in response.context["form"]
            if field.is_hidden
        }
        self.assertEqual(
            browser.post("/o/authorize/", {**fields, "allow": "true"}).status_code, 403
        )
        self.assertEqual(
            browser.post(
                "/o/authorize/",
                {
                    **fields,
                    "allow": "true",
                    "csrfmiddlewaretoken": browser.cookies["csrftoken"].value,
                },
            ).status_code,
            302,
        )
        rotated = jwk.JWK.generate(kty="RSA", size=2048)
        config = {
            **settings.OAUTH2_PROVIDER,
            "OIDC_RSA_PRIVATE_KEY": rotated.export_to_pem(
                private_key=True, password=None
            ).decode(),
            "OIDC_RSA_PRIVATE_KEYS_INACTIVE": [
                self.key.export_to_pem(private_key=True, password=None).decode()
            ],
        }
        with override_settings(OAUTH2_PROVIDER=config):
            keys = browser.get("/o/.well-known/jwks.json").json()["keys"]
            self.assertEqual(len(keys), 2)
            self.assertTrue(all("d" not in key for key in keys))
