from contextvars import ContextVar

active_role = ContextVar("audit_active_role", default="")


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = active_role.set(request.session.get("active_role") or "")
        try:
            return self.get_response(request)
        finally:
            active_role.reset(token)
