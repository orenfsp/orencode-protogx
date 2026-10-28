from datetime import timedelta
from io import BytesIO

from django.utils import timezone
from docx import Document

from apps.extensions.models import JudgingDocument

from .optional_helpers import OptionalCase


class JudgingTests(OptionalCase):
    def test_own_panel_report_formats_and_cross_user_denial(self):
        self.login(self.judge, "judge")
        response = self.post("judging-documents/", {"kind": "panel", "competition": self.competition.pk})
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertEqual(self.client.get(f"/api/v1/judging-documents/{pk}/download/").content[:4], b"%PDF")
        docx = self.client.get(f"/api/v1/judging-documents/{pk}/download/?file_format=docx")
        self.assertIn(self.judge.full_name, " ".join(c.text for t in Document(BytesIO(docx.content)).tables for r in t.rows for c in r.cells))
        self.competition.ends_at = timezone.now() + timedelta(days=10)
        self.competition.save()
        report = self.post("judging-documents/", {"kind": "judge_work"})
        self.assertEqual(JudgingDocument.objects.get(pk=report.data["id"]).snapshot["rows"], [])
        self.login(self.other, "athlete")
        self.assertEqual(self.client.get(f"/api/v1/judging-documents/{pk}/download/").status_code, 403)

    def test_unassigned_judge_cannot_export_other_panel(self):
        self.login(self.judge, "judge")
        self.assignment.delete()
        self.assertEqual(self.post("judging-documents/", {"kind": "panel", "competition": self.competition.pk}).status_code, 403)
        self.login(self.federation, "federation")
        self.assertEqual(self.post("judging-documents/", {"kind": "judge_work", "judge": self.judge.pk, "start_year": 2026, "end_year": 2025}).status_code, 400)
