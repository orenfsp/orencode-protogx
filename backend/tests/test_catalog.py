from django.test import TestCase
from rest_framework.test import APIClient


class CatalogTests(TestCase):
    def test_six_disciplines_available(self):
        response = APIClient().get("/api/v1/disciplines/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 6)
        self.assertEqual(len({item["code"] for item in response.data}), 6)
