from django.conf import settings


def public_settings(request):
    return {"fsp_public_url": settings.FSP_PUBLIC_URL}
