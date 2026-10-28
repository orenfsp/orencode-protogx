from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.competitions.models import ProtocolPublication
from apps.extensions.models import ReviewCase, ReviewPolicy
from apps.ratings.models import RatingContribution

from .optional_helpers import OptionalCase


class ReviewTests(OptionalCase):
    def open_case(self):
        self.login(self.athlete,"athlete")
        response=self.post("reviews/",{"kind":"appeal","application":self.application.pk,"statement":"Прошу проверить результат; вымышленные данные"})
        self.assertEqual(response.status_code,201,response.data)
        return response.data["id"]

    def test_reasoned_correction_is_versioned_and_recalculates(self):
        pk=self.open_case()
        old=self.publication.snapshot.copy()
        self.login(self.federation,"federation")
        started=self.post(f"reviews/{pk}/action/",{"action":"start","expected_revision":1,"reason":"Принято к проверке"})
        self.assertEqual(started.status_code,200,started.data)
        corrected=self.post(f"reviews/{pk}/action/",{"action":"accept","expected_revision":2,"reason":"Исправлена подтверждённая ошибка","correction":{"status":"classified","place":2,"score":"90","metrics":{"solved_tasks":2}}})
        self.assertEqual(corrected.status_code,200,corrected.data)
        self.assertEqual(ProtocolPublication.objects.count(),2)
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.snapshot,old)
        self.assertEqual(self.competition.protocols.first().snapshot["rows"][0]["place"],2)
        self.assertTrue(RatingContribution.objects.filter(publication_id=corrected.data["publication"],is_current=True).exists())
        self.assertEqual(ReviewCase.objects.get(pk=pk).history.count(),3)

    def test_private_upload_tampering_deadlines_and_closed_evidence(self):
        pk=self.open_case()
        bad=self.client.post(f"/api/v1/reviews/{pk}/evidence/",{"description":"Недопустимый файл","file":SimpleUploadedFile("evil.svg",b"<svg onload='evil()'/>",content_type="image/svg+xml")},format="multipart")
        self.assertEqual(bad.status_code,400)
        good=self.client.post(f"/api/v1/reviews/{pk}/evidence/",{"description":"Тестовый лог","file":SimpleUploadedFile("log.txt",b"fictional log",content_type="text/plain")},format="multipart")
        self.assertEqual(good.status_code,201,good.data)
        self.login(self.other,"athlete")
        self.assertEqual(self.client.get(f"/api/v1/reviews/evidence/{good.data['id']}/").status_code,403)
        self.assertEqual(self.post(f"reviews/{pk}/action/",{"action":"start","expected_revision":1,"reason":"Нельзя"}).status_code,403)
        ReviewPolicy.objects.create(competition=self.competition,appeal_deadline=timezone.now()-timedelta(days=1),source_url="https://example.test/demo-rules",rule_note="Демонстрационный срок")
        self.login(self.athlete,"athlete")
        self.assertEqual(self.post("reviews/",{"kind":"appeal","application":self.application.pk,"statement":"Слишком поздно"}).status_code,400)

    def test_judge_conflict_and_stale_revision(self):
        pk=self.open_case()
        self.result.updated_by=self.judge
        self.result.save()
        self.login(self.judge,"judge")
        self.assertEqual(self.post(f"reviews/{pk}/action/",{"action":"start","expected_revision":1,"reason":"Конфликт"}).status_code,403)
        self.login(self.federation,"federation")
        self.assertEqual(self.post(f"reviews/{pk}/action/",{"action":"start","expected_revision":999,"reason":"Устарело"}).status_code,400)
