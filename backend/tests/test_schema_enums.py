from django.test import SimpleTestCase
from drf_spectacular.generators import SchemaGenerator


class SchemaEnumTests(SimpleTestCase):
    def test_qualification_enum_names_and_wire_values(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)
        components = schema["components"]["schemas"]
        expected = {
            "SportRankEnum": ["youth_3", "youth_2", "youth_1", "adult_3", "adult_2", "adult_1", "cms", "ms", "msmk"],
            "JudgeCategoryEnum": ["youth", "third", "second", "first", "all_russian"],
            "QualificationReviewStatusEnum": ["pending", "approved", "rejected"],
            "DecisionStatusEnum": ["approved", "rejected"],
        }
        for name, values in expected.items():
            with self.subTest(name=name):
                self.assertEqual(components[name]["enum"], values)
        aliases = {
            "RankEnum": "SportRankEnum", "RequestedRankEnum": "SportRankEnum",
            "CategoryEnum": "JudgeCategoryEnum", "RequestedCategoryEnum": "JudgeCategoryEnum",
            "Status41aEnum": "QualificationReviewStatusEnum", "StatusDc7Enum": "DecisionStatusEnum",
        }
        for old_name, canonical_name in aliases.items():
            with self.subTest(alias=old_name):
                self.assertEqual(components[old_name]["$ref"], f"#/components/schemas/{canonical_name}")
        self.assertEqual(components["RankApplicationCreate"]["properties"]["requested_rank"]["$ref"], "#/components/schemas/SportRankEnum")
        self.assertEqual(components["CategoryApplicationCreate"]["properties"]["requested_category"]["$ref"], "#/components/schemas/JudgeCategoryEnum")
        self.assertEqual(components["DecisionInput"]["properties"]["status"]["$ref"], "#/components/schemas/DecisionStatusEnum")
