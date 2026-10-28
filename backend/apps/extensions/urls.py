from django.urls import path

from .assessment import (
    AssessmentView,
    AttemptCreateView,
    AttestationApproveView,
    AttestationCreateView,
    NormCreateView,
)
from .certificates import (
    CertificateDownloadView,
    CertificateRevokeView,
    CertificatesView,
    CertificateVerifyView,
)
from .development import DevelopmentView, IndicatorEvidenceView
from .judging import JudgingDocumentsView, JudgingDownloadView
from .ministry import MinistryView
from .newcomer import NewcomerView
from .notifications import NotificationsView
from .progression import ProgressionRuleCreateView, ProgressionView
from .reviews import (
    EvidenceDownloadView,
    ReviewActionView,
    ReviewCasesView,
    ReviewEvidenceView,
    ReviewPolicyView,
)
from .training import (
    AttendanceView,
    EnrollmentView,
    GroupCreateView,
    OrganizationCreateView,
    SessionCreateView,
    TrainingView,
)

urlpatterns = [
    path("reviews/", ReviewCasesView.as_view()),
    path("reviews/policies/", ReviewPolicyView.as_view()),
    path("reviews/<int:pk>/action/", ReviewActionView.as_view()),
    path("reviews/<int:pk>/evidence/", ReviewEvidenceView.as_view()),
    path("reviews/evidence/<int:pk>/", EvidenceDownloadView.as_view()),
    path("notifications/", NotificationsView.as_view()),
    path("newcomer/", NewcomerView.as_view()),
    path("ministry/", MinistryView.as_view()),
    path("development/", DevelopmentView.as_view()),
    path("development/evidence/", IndicatorEvidenceView.as_view()),
    path("progression/", ProgressionView.as_view()),
    path("progression/rules/", ProgressionRuleCreateView.as_view()),
    path("assessment/", AssessmentView.as_view()),
    path("assessment/norms/", NormCreateView.as_view()),
    path("assessment/attempts/", AttemptCreateView.as_view()),
    path("assessment/attestations/", AttestationCreateView.as_view()),
    path("assessment/attestations/<int:pk>/approve/", AttestationApproveView.as_view()),
    path("training/", TrainingView.as_view()),
    path("training/organizations/", OrganizationCreateView.as_view()),
    path("training/groups/", GroupCreateView.as_view()),
    path("training/enroll/", EnrollmentView.as_view()),
    path("training/sessions/", SessionCreateView.as_view()),
    path("training/attendance/", AttendanceView.as_view()),
    path("judging-documents/", JudgingDocumentsView.as_view()),
    path("judging-documents/<int:pk>/download/", JudgingDownloadView.as_view()),
    path("certificates/", CertificatesView.as_view()),
    path("certificates/<int:pk>/download/", CertificateDownloadView.as_view()),
    path("certificates/<int:pk>/revoke/", CertificateRevokeView.as_view()),
    path("certificates/verify/<uuid:public_id>/", CertificateVerifyView.as_view()),
]
