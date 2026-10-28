from django.urls import path

from .certificates import (
    CertificateDownloadView,
    CertificateRevokeView,
    CertificatesView,
    CertificateVerifyView,
)
from .judging import JudgingDocumentsView, JudgingDownloadView
from .notifications import NotificationsView

urlpatterns = [
    path("notifications/", NotificationsView.as_view()),
    path("judging-documents/", JudgingDocumentsView.as_view()),
    path("judging-documents/<int:pk>/download/", JudgingDownloadView.as_view()),
    path("certificates/", CertificatesView.as_view()),
    path("certificates/<int:pk>/download/", CertificateDownloadView.as_view()),
    path("certificates/<int:pk>/revoke/", CertificateRevokeView.as_view()),
    path("certificates/verify/<uuid:public_id>/", CertificateVerifyView.as_view()),
]
