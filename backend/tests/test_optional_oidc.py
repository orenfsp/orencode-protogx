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
    def setUp(self):
        super().setUp()
        self.key=jwk.JWK.generate(kty="RSA",size=2048)
        config={**settings.OAUTH2_PROVIDER,"OIDC_ENABLED":True,"OIDC_RSA_PRIVATE_KEY":self.key.export_to_pem(private_key=True,password=None).decode(),"OIDC_ISS_ENDPOINT":"http://testserver","OIDC_USERINFO_ENDPOINT":"http://testserver/o/userinfo/","ALWAYS_RELOAD_OAUTHLIB_CORE":True}
        self.override=override_settings(FSP_OIDC_ENABLED=True,FSP_OIDC_ISSUER="http://testserver",OAUTH2_PROVIDER=config)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.browser=Client()
        self.browser.force_login(self.athlete)
        self.app=Application.objects.create(name="Вымышленный OIDC клиент",user=self.federation,client_type="public",authorization_grant_type="authorization-code",redirect_uris="http://localhost:9012/callback",algorithm="RS256")
        OIDCClientPolicy.objects.create(application=self.app,scopes=["openid","profile","fsp_roles","fsp_disciplines","fsp_rank"])
        self.verifier="x"*64
        self.challenge=base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b"=").decode()

    def parameters(self,scope="openid profile fsp_roles"):
        return {"client_id":self.app.client_id,"response_type":"code","redirect_uri":"http://localhost:9012/callback","scope":scope,"state":"fictional-state-123","nonce":"fictional-nonce-123","code_challenge":self.challenge,"code_challenge_method":"S256"}

    def authorize(self,scope="openid profile fsp_roles"):
        params=self.parameters(scope)
        response=self.browser.get("/o/authorize/?"+urlencode(params))
        self.assertEqual(response.status_code,200,response.content[:500])
        response=self.browser.post("/o/authorize/",{**params,"allow":"true"})
        self.assertEqual(response.status_code,302,response.content[:500])
        query=parse_qs(urlsplit(response["Location"]).query)
        self.assertEqual(query["state"],[params["state"]])
        return query["code"][0]

    def exchange(self,code,verifier=None):
        return self.browser.post("/o/token/",{"client_id":self.app.client_id,"grant_type":"authorization_code","code":code,"redirect_uri":"http://localhost:9012/callback","code_verifier":verifier or self.verifier})

    def test_full_code_pkce_consent_jwks_userinfo_revoke(self):
        discovery=self.browser.get("/o/.well-known/openid-configuration")
        self.assertEqual(discovery.status_code,200,discovery.content)
        self.assertEqual(discovery.json()["code_challenge_methods_supported"],["S256"])
        code=self.authorize()
        response=self.exchange(code)
        self.assertEqual(response.status_code,200,response.content)
        tokens=response.json()
        self.assertNotIn("refresh_token",tokens)
        keys=self.browser.get("/o/.well-known/jwks.json").json()
        verified=jwt.JWT(jwt=tokens["id_token"],key=jwk.JWKSet.from_json(json.dumps(keys)),check_claims={"iss":"http://testserver","aud":self.app.client_id,"nonce":"fictional-nonce-123","exp":None})
        claims=json.loads(verified.claims)
        self.assertEqual(claims["name"],self.athlete.full_name)
        self.assertLessEqual(claims["exp"]-claims["iat"],300)
        self.assertEqual(AccessToken.objects.get().token,"")
        info=self.browser.get("/o/userinfo/",HTTP_AUTHORIZATION="Bearer "+tokens["access_token"])
        self.assertEqual(info.status_code,200,info.content)
        self.assertEqual(info.json()["sub"],claims["sub"])
        self.assertNotIn("ranks",info.json())
        self.assertEqual(self.exchange(code).status_code,400)
        revoked=self.browser.post("/o/revoke_token/",{"client_id":self.app.client_id,"token":tokens["access_token"]})
        self.assertEqual(revoked.status_code,200,revoked.content)
        self.assertEqual(self.browser.get("/o/userinfo/",HTTP_AUTHORIZATION="Bearer "+tokens["access_token"]).status_code,401)

    def test_pkce_wrong_redirect_nonce_missing_and_form_tampering(self):
        params=self.parameters()
        for key,value in [("code_challenge_method","plain"),("nonce",""),("state","")]:
            self.assertEqual(self.browser.get("/o/authorize/?"+urlencode({**params,key:value})).status_code,400)
        response=self.browser.get("/o/authorize/?"+urlencode({**params,"redirect_uri":"https://evil.example.test/callback"}))
        self.assertNotEqual(response.status_code,302)
        self.browser.get("/o/authorize/?"+urlencode(params))
        self.assertEqual(self.browser.post("/o/authorize/",{**params,"scope":"openid profile fsp_rank","allow":"true"}).status_code,400)
        code=self.authorize()
        self.assertEqual(self.exchange(code,"wrong"*16).status_code,400)

    def test_consent_revocation_expiry_and_disabled_client(self):
        tokens=self.exchange(self.authorize("openid")).json()
        info=self.browser.get("/o/userinfo/",HTTP_AUTHORIZATION="Bearer "+tokens["access_token"])
        self.assertEqual(list(info.json()),["sub"])
        AccessToken.objects.update(expires=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.browser.get("/o/userinfo/",HTTP_AUTHORIZATION="Bearer "+tokens["access_token"]).status_code,401)
        tokens=self.exchange(self.authorize()).json()
        self.login(self.athlete,"athlete")
        consent=OIDCSharingConsent.objects.filter(user=self.athlete).first()
        self.assertEqual(self.post(f"fsp-id/consents/{consent.pk}/revoke/").status_code,200)
        self.assertEqual(self.browser.get("/o/userinfo/",HTTP_AUTHORIZATION="Bearer "+tokens["access_token"]).status_code,401)
        self.login(self.federation,"federation")
        self.assertEqual(self.post(f"fsp-id/clients/{self.app.pk}/disable/").status_code,200)
        self.assertEqual(Grant.objects.count(),0)
