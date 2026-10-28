from drf_spectacular.extensions import OpenApiAuthenticationExtension


class IntegrationBearerScheme(OpenApiAuthenticationExtension):
    target_class = "apps.extensions.integrations.IntegrationAuthentication"
    name = "integrationBearer"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "description": "Opaque expiring integration token; client scopes and event grants are checked on the server. Not a session or FSP ID token.",
        }
