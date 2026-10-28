import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-development-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,api").split(",")
CSRF_TRUSTED_ORIGINS = [origin for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if origin]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "apps.accounts",
    "apps.catalogs",
    "apps.competitions",
    "apps.qualifications",
    "apps.ratings",
    "apps.teams",
    "apps.extensions",
    "oauth2_provider",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.debug", "django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if os.environ.get("DATABASE_ENGINE") == "sqlite":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "local.sqlite3"}}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "fsp"),
        "USER": os.environ.get("POSTGRES_USER", "fsp"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "fsp_local"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}, {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}, {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_RATES": {"login": "5/min"},
}
SPECTACULAR_SETTINGS = {
    "TITLE": "FSP OrenKod API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "SportRankEnum": "apps.qualifications.models.SportRank",
        "JudgeCategoryEnum": "apps.qualifications.models.JudgeCategory",
        "QualificationReviewStatusEnum": "apps.qualifications.models.ReviewStatus",
        "DecisionStatusEnum": [("approved", "approved"), ("rejected", "rejected")],
    },
    # Keep existing component names available for consumers of the earlier schema.
    "APPEND_COMPONENTS": {"schemas": {
        "RankEnum": {"$ref": "#/components/schemas/SportRankEnum"},
        "RequestedRankEnum": {"$ref": "#/components/schemas/SportRankEnum"},
        "CategoryEnum": {"$ref": "#/components/schemas/JudgeCategoryEnum"},
        "RequestedCategoryEnum": {"$ref": "#/components/schemas/JudgeCategoryEnum"},
        "Status41aEnum": {"$ref": "#/components/schemas/QualificationReviewStatusEnum"},
        "StatusDc7Enum": {"$ref": "#/components/schemas/DecisionStatusEnum"},
    }},
}
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Asia/Yekaterinburg"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Optional features reuse the existing identities, session/CSRF and audit models.
# SMTP is opt-in; local default does not contact an external provider.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "0") == "1"
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "fsp@example.test")
PROTOCOL_PDF_FONT = os.environ.get("PROTOCOL_PDF_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FSP_PUBLIC_URL = os.environ.get("FSP_PUBLIC_URL", "http://127.0.0.1:3000").rstrip("/")
INTEGRATION_ENCRYPTION_KEY = os.environ.get("INTEGRATION_ENCRYPTION_KEY", "")
FSP_WEBHOOK_HOSTS = [h for h in os.environ.get("FSP_WEBHOOK_HOSTS", "").split(",") if h]
FSP_WEBHOOK_ALLOW_LOOPBACK = os.environ.get("FSP_WEBHOOK_ALLOW_LOOPBACK", "0") == "1"

OIDC_KEY_FILE = os.environ.get("FSP_OIDC_PRIVATE_KEY_FILE", "")
OIDC_PRIVATE_KEY = Path(OIDC_KEY_FILE).read_text(encoding="utf-8") if OIDC_KEY_FILE else ""
FSP_OIDC_ENABLED = os.environ.get("FSP_OIDC_ENABLED", "0") == "1" and bool(OIDC_PRIVATE_KEY)
FSP_OIDC_ISSUER = os.environ.get("FSP_OIDC_ISSUER", "http://127.0.0.1:8000").rstrip("/")
LOGIN_URL = "/o/login/"
OAUTH2_PROVIDER_APPLICATION_MODEL = "oauth2_provider.Application"
OAUTH2_PROVIDER = {
    "OIDC_ENABLED": FSP_OIDC_ENABLED,
    "OIDC_RSA_PRIVATE_KEY": OIDC_PRIVATE_KEY,
    "OIDC_RSA_PRIVATE_KEYS_INACTIVE": [Path(p).read_text(encoding="utf-8") for p in os.environ.get("FSP_OIDC_INACTIVE_KEY_FILES", "").split(os.pathsep) if p],
    "OIDC_ISS_ENDPOINT": FSP_OIDC_ISSUER,
    "OIDC_USERINFO_ENDPOINT": FSP_OIDC_ISSUER + "/o/userinfo/",
    "OAUTH2_VALIDATOR_CLASS": "apps.extensions.oidc.FSPValidator",
    "OAUTH2_BACKEND_CLASS": "apps.extensions.oidc.FSPCore",
    "SCOPES": {"openid": "Псевдонимный идентификатор", "profile": "ФИО", "fsp_roles": "Назначенные роли", "fsp_disciplines": "Спортивные дисциплины", "fsp_rank": "Действующие разряды"},
    "DEFAULT_SCOPES": ["openid"],
    "ACCESS_TOKEN_EXPIRE_SECONDS": 300,
    "ID_TOKEN_EXPIRE_SECONDS": 300,
    "AUTHORIZATION_CODE_EXPIRE_SECONDS": 60,
    "PKCE_REQUIRED": True,
    "COMPLIANT_BCP_RFC9700_PKCE_METHOD": True,
    "COMPLIANT_BCP_RFC9700_PKCE_REQUIRED": True,
    "COMPLIANT_BCP_RFC9700_TOKEN_STORAGE": True,
    "COMPLIANT_BCP_RFC9700_AUTHZ_RESPONSE_ISS": True,
    "COMPLIANT_BCP_RFC9700_IMPLICIT_GRANT": True,
    "COMPLIANT_BCP_RFC9700_PASSWORD_GRANT": True,
    "OIDC_RESPONSE_TYPES_SUPPORTED": ["code"],
    "OIDC_RP_INITIATED_LOGOUT_ENABLED": True,
    "OIDC_RP_INITIATED_LOGOUT_STRICT_REDIRECT_URIS": True,
    "OIDC_RP_INITIATED_LOGOUT_ACCEPT_EXPIRED_TOKENS": False,
    "OIDC_JWKS_MAX_AGE_SECONDS": 60,
    "ALLOW_URI_WILDCARDS": False,
}
