from datetime import date
from decimal import Decimal
from io import BytesIO

from docx import Document

from apps.competitions.services import publish_protocol
from apps.extensions.awards import award_candidates
from apps.extensions.models import AwardRate, AwardScheme

from .optional_helpers import OptionalCase


class AwardTests(OptionalCase):
    def test_automatic_candidates_calculation_package_and_stale_evidence(self):
        year=self.competition.starts_at.year
        scheme=AwardScheme.objects.create(year=year,version=1,name="Вымышленные премии",aggregation="best",deadline=date(year+1,2,1))
        AwardRate.objects.create(scheme=scheme,level="regional",place=1,amount=Decimal("123.45"))
        candidates,_=award_candidates(scheme)
        self.assertEqual(candidates[0]["total"],"123.45")
        self.login(self.federation,"federation")
        prepared=self.post("awards/prepare/",{"scheme":scheme.pk})
        self.assertEqual(prepared.status_code,201,prepared.data)
        pk=prepared.data["id"]
        doc=self.client.get(f"/api/v1/awards/{pk}/download/")
        text=" ".join(p.text for p in Document(BytesIO(doc.content)).paragraphs)
        self.assertIn("ИНН: ************",text)
        self.assertIn("ДЕМОНСТРАЦИЯ",text)
        self.assertEqual(self.post(f"awards/{pk}/action/",{"status":"sent","expected_revision":1,"reason":"Проверено в демо"}).status_code,200)
        publish_protocol(self.competition,self.federation,"Новая версия доказательства")
        self.assertEqual(self.post(f"awards/{pk}/action/",{"status":"awarded","expected_revision":2,"reason":"Данные устарели"}).status_code,400)
        self.login(self.athlete,"athlete")
        self.assertEqual(self.client.get("/api/v1/awards/").status_code,403)
