class PrivateExtensionResponses:
    prefixes = tuple(
        "/api/v1/" + name
        for name in [
            "certificates/",
            "judging-documents/",
            "training/",
            "assessment/",
            "progression/",
            "development/",
            "reviews/",
            "awards/",
            "ministry/",
            "integrations/",
            "external/",
            "fsp-id/",
            "notifications/",
        ]
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.prefixes) or request.path.startswith("/o/"):
            response["Cache-Control"] = "private, no-store"
            # Same-origin form POSTs need their origin for Django CSRF checks;
            # cross-origin OIDC redirects still disclose no Referer.
            response["Referrer-Policy"] = (
                "same-origin" if request.path.startswith("/o/") else "no-referrer"
            )
        return response
