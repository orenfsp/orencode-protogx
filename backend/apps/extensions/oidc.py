import hashlib
import hmac
import re
import secrets
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from oauth2_provider.models import AccessToken, Application, Grant, RefreshToken
from oauth2_provider.oauth2_backends import OAuthLibCore
from oauth2_provider.oauth2_validators import OAuth2Validator
from oauth2_provider.views import (
    AuthorizationView,
    ConnectDiscoveryInfoView,
    JwksInfoView,
    RevokeTokenView,
    RPInitiatedLogoutView,
    TokenView,
    UserInfoView,
)
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Guardian, has_current_consent
from apps.competitions.models import Application as SportApplication
from apps.competitions.models import CoachAthleteLink
from apps.competitions.services import age_on, audit, require_role
from apps.qualifications.models import SportRankHistory

from .models import OIDCClientPolicy, OIDCSharingConsent


class FSPCore(OAuthLibCore):
    def _extract_params(self,request):
        # DOT 3.4's userinfo wrapper passes a relative URI to oauthlib, unlike its
        # verify_request wrapper. RFC 8707 audience validation needs an absolute
        # URI. Preserve Django's validated host/scheme and the library parser.
        uri,method,body,headers=super()._extract_params(request)
        return request.build_absolute_uri(uri),method,body,headers


def enabled_policy(application):
    return bool(settings.FSP_OIDC_ENABLED and application and OIDCClientPolicy.objects.filter(application=application,enabled=True).exists())


def can_share(user):
    return bool(user and user.is_active and has_current_consent(user) and user.date_of_birth and (age_on(user.date_of_birth,timezone.localdate())>=18 or Guardian.objects.filter(minor=user,confirmation_status="verified").exists()))


def sharing_consent(user,application,scopes):
    if not can_share(user) or not enabled_policy(application):
        return False
    policy=OIDCClientPolicy.objects.get(application=application)
    if not set(scopes).issubset(policy.scopes):
        return False
    return any(set(scopes).issubset(c.scopes) for c in OIDCSharingConsent.objects.filter(user=user,application=application,revoked_at=None))


class FSPValidator(OAuth2Validator):
    oidc_claim_scope={"sub":"openid","name":"profile","roles":"fsp_roles","disciplines":"fsp_disciplines","ranks":"fsp_rank"}

    def validate_client_id(self,client_id,request,*args,**kwargs):
        return super().validate_client_id(client_id,request,*args,**kwargs) and enabled_policy(request.client)

    def validate_scopes(self,client_id,scopes,client,request,*args,**kwargs):
        policy=OIDCClientPolicy.objects.filter(application=client,enabled=True).first()
        return bool(policy and "openid" in scopes and set(scopes).issubset(policy.scopes) and super().validate_scopes(client_id,scopes,client,request,*args,**kwargs))

    def validate_code(self,client_id,code,client,request,*args,**kwargs):
        return super().validate_code(client_id,code,client,request,*args,**kwargs) and sharing_consent(request.user,client,request.scopes)

    def validate_grant_type(self,client_id,grant_type,client,request,*args,**kwargs):
        # This provider deliberately has no password, implicit or refresh grants.
        return grant_type=="authorization_code" and enabled_policy(client) and super().validate_grant_type(client_id,grant_type,client,request,*args,**kwargs)

    def validate_bearer_token(self,token,scopes,request):
        return super().validate_bearer_token(token,scopes,request) and sharing_consent(request.user,request.client,request.scopes)

    def _save_bearer_token(self,token,request,*args,**kwargs):
        token.pop("refresh_token",None)
        request.resource=[settings.FSP_OIDC_ISSUER+"/o/userinfo/"]
        super()._save_bearer_token(token,request,*args,**kwargs)
        audit(request.user,"oidc.token_issued",request.client,after={"scopes":list(request.scopes)})

    def get_additional_claims(self,request):
        user=request.user
        today=timezone.localdate()
        disciplines=set(SportApplication.objects.filter(athlete=user).values_list("competition__discipline__code",flat=True))
        disciplines.update(CoachAthleteLink.objects.filter(coach=user,status="confirmed").values_list("discipline__code",flat=True))
        return {"sub":hmac.new(settings.SECRET_KEY.encode(),f"fsp:{request.client.client_id}:{user.pk}".encode(),hashlib.sha256).hexdigest(),"name":user.full_name,"roles":list(user.role_assignments.values_list("role",flat=True)),"disciplines":sorted(disciplines),"ranks":[{"discipline":r.discipline.code,"rank":r.rank,"valid_until":r.valid_until.isoformat()} for r in SportRankHistory.objects.filter(athlete=user,assigned_on__lte=today,valid_until__gte=today).select_related("discipline")]}

    def get_discovery_claims(self,request):
        return list(self.oidc_claim_scope)


def authorization_binding(data):
    return {key:data.get(key,"") for key in ["client_id","redirect_uri","scope","state","nonce","response_type","code_challenge","code_challenge_method","claims","resource"]}


class FSPAuthorizationView(AuthorizationView):
    template_name="extensions/oidc_authorize.html"

    def get(self,request,*args,**kwargs):
        if not settings.FSP_OIDC_ENABLED:
            return HttpResponse("ФСП ID не настроен",status=503)
        if not can_share(request.user):
            return HttpResponse("Необходимо действующее согласие; для несовершеннолетнего — проверенное согласие представителя",status=403)
        data=request.GET
        if data.get("response_type")!="code" or not data.get("state") or not data.get("nonce") or data.get("code_challenge_method")!="S256" or not re.fullmatch(r"[A-Za-z0-9_-]{43}",data.get("code_challenge","")):
            return HttpResponse("Требуются code, state, nonce и PKCE S256",status=400)
        response=super().get(request,*args,**kwargs)
        if response.status_code==200 and not getattr(response,"context_data",{}).get("error"):
            pending=request.session.get("oidc_pending",{})
            pending={k:v for k,v in pending.items() if timezone.now().timestamp()-v["at"]<600}
            if len(pending)>=5:
                pending={}
            pending[hashlib.sha256(data["state"].encode()).hexdigest()]={"values":authorization_binding(data),"at":timezone.now().timestamp(),"user":request.user.pk}
            request.session["oidc_pending"]=pending
        response["Cache-Control"]="no-store"
        response["Referrer-Policy"]="no-referrer"
        return response

    @transaction.atomic
    def form_valid(self,form):
        if not settings.FSP_OIDC_ENABLED or not can_share(self.request.user):
            return HttpResponse("Передача данных недоступна",status=403)
        pending=self.request.session.get("oidc_pending",{})
        key=hashlib.sha256(form.cleaned_data.get("state","").encode()).hexdigest()
        binding=pending.pop(key,None)
        self.request.session["oidc_pending"]=pending
        values=authorization_binding(form.cleaned_data)
        if not binding or binding["user"]!=self.request.user.pk or timezone.now().timestamp()-binding["at"]>600 or binding["values"]!=values:
            return HttpResponse("Запрос согласия истёк или изменён",status=400)
        application=Application.objects.filter(client_id=form.cleaned_data["client_id"]).first()
        policy=OIDCClientPolicy.objects.filter(application=application,enabled=True).first()
        scopes=form.cleaned_data["scope"].split()
        if not policy or not set(scopes).issubset(policy.scopes):
            return HttpResponse("Разрешения клиента отозваны",status=400)
        response=super().form_valid(form)
        if response.status_code==302 and form.cleaned_data["allow"] and "code" in parse_qs(urlsplit(response["Location"]).query):
            consent=OIDCSharingConsent.objects.create(user=self.request.user,application=application,scopes=scopes)
            audit(self.request.user,"oidc.consent_granted",consent,after={"application":application.pk,"scopes":scopes})
        return response


class FSPLoginView(LoginView):
    template_name="extensions/oidc_login.html"
    redirect_authenticated_user=True

    def post(self,request,*args,**kwargs):
        key="oidc-login:"+hashlib.sha256(request.META.get("REMOTE_ADDR","").encode()).hexdigest()
        if not cache.add(key,1,60):
            try:
                attempts=cache.incr(key)
            except ValueError:
                attempts=1
            if attempts>5:
                return HttpResponse("Слишком много попыток. Повторите через минуту.",status=429)
        return super().post(request,*args,**kwargs)

    def form_valid(self,form):
        response=super().form_valid(form)
        self.request.session["active_role"]=form.get_user().role_assignments.values_list("role",flat=True).first()
        return response


class OIDCClientInput(serializers.Serializer):
    name=serializers.CharField(max_length=200)
    client_type=serializers.ChoiceField(choices=["public","confidential"])
    redirect_uris=serializers.ListField(child=serializers.URLField(),allow_empty=False,max_length=10)
    post_logout_redirect_uris=serializers.ListField(child=serializers.URLField(),required=False,default=list,max_length=10)
    scopes=serializers.ListField(child=serializers.ChoiceField(choices=list(settings.OAUTH2_PROVIDER["SCOPES"])),allow_empty=False)

    def validate(self,data):
        for uri in data["redirect_uris"]+data["post_logout_redirect_uris"]:
            parsed=urlsplit(uri)
            if parsed.fragment or parsed.username or parsed.password or "*" in uri or (parsed.scheme!="https" and not (settings.DEBUG and parsed.scheme=="http" and parsed.hostname in ["127.0.0.1","localhost"])):
                raise serializers.ValidationError("Точный HTTPS redirect URI обязателен; localhost HTTP разрешён только в DEBUG")
        if "openid" not in data["scopes"]:
            raise serializers.ValidationError("Необходим scope openid")
        return data


class OIDCClientsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        require_role(request,"federation")
        return Response({"items":[{"id":p.application_id,"name":p.application.name,"client_id":p.application.client_id,"client_type":p.application.client_type,"enabled":p.enabled,"details":p.scopes} for p in OIDCClientPolicy.objects.select_related("application")],"notice":"ФСП ID использует authorization code + PKCE S256. "+("Провайдер настроен." if settings.FSP_OIDC_ENABLED else "Провайдер выключен до настройки ключа и issuer; основной сервис работает независимо."),"enabled":settings.FSP_OIDC_ENABLED,"options":{}})

    @extend_schema(request=OIDCClientInput,responses={201:OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self,request):
        require_role(request,"federation")
        serializer=OIDCClientInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data=serializer.validated_data
        secret=secrets.token_urlsafe(48)
        application=Application.objects.create(name=data["name"],user=request.user,client_type=data["client_type"],authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,client_secret=secret,hash_client_secret=True,redirect_uris=" ".join(data["redirect_uris"]),post_logout_redirect_uris=" ".join(data["post_logout_redirect_uris"]),algorithm=Application.RS256_ALGORITHM,skip_authorization=False)
        policy=OIDCClientPolicy.objects.create(application=application,scopes=data["scopes"])
        audit(request.user,"oidc.client_created",policy,after={"application":application.pk,"scopes":data["scopes"]})
        response=Response({"id":application.pk,"client_id":application.client_id,"client_secret":secret if application.client_type=="confidential" else ""},status=201)
        response["Cache-Control"]="no-store"
        return response


class OIDCClientDisableView(APIView):
    @extend_schema(request=None,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        require_role(request,"federation")
        policy=get_object_or_404(OIDCClientPolicy.objects.select_for_update(),application_id=pk)
        policy.enabled=False
        policy.save(update_fields=["enabled"])
        Grant.objects.filter(application_id=pk).delete()
        RefreshToken.objects.filter(application_id=pk).delete()
        AccessToken.objects.filter(application_id=pk).delete()
        audit(request.user,"oidc.client_disabled",policy)
        return Response({"enabled":False})


class OIDCConsentRevokeView(APIView):
    @extend_schema(request=None,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        consent=get_object_or_404(OIDCSharingConsent,user=request.user,pk=pk)
        OIDCSharingConsent.objects.filter(user=request.user,application=consent.application,revoked_at=None).update(revoked_at=timezone.now())
        Grant.objects.filter(user=request.user,application=consent.application).delete()
        RefreshToken.objects.filter(user=request.user,application=consent.application).delete()
        AccessToken.objects.filter(user=request.user,application=consent.application).delete()
        audit(request.user,"oidc.consent_revoked",consent)
        return Response({"revoked":True})


class OIDCConsentsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        consents=OIDCSharingConsent.objects.filter(user=request.user).select_related("application").order_by("-pk")
        return Response({"items":[{"id":c.pk,"name":c.application.name,"details":c.scopes,"status":"revoked" if c.revoked_at else "active"} for c in consents],"notice":"Отзыв согласия немедленно отзывает токены и незавершённые коды этого приложения. Для нового входа потребуется новое согласие.","options":{"consents":[{"value":c.pk,"label":f"{c.pk}: {c.application.name}"} for c in consents if not c.revoked_at]}})


# Exclude DOT self-service registration, dynamic registration, device and password
# routes. Only federation-managed applications can participate in this provider.
oidc_patterns=( [
    path("authorize/",FSPAuthorizationView.as_view(),name="authorize"),
    path("token/",TokenView.as_view(),name="token"),
    path("revoke_token/",RevokeTokenView.as_view(),name="revoke-token"),
    path("userinfo/",UserInfoView.as_view(),name="user-info"),
    path(".well-known/openid-configuration",ConnectDiscoveryInfoView.as_view(),name="oidc-connect-discovery-info"),
    path(".well-known/jwks.json",JwksInfoView.as_view(),name="jwks-info"),
    path("logout/",RPInitiatedLogoutView.as_view(),name="rp-initiated-logout"),
    path("login/",FSPLoginView.as_view(),name="login"),
], "oauth2_provider")
