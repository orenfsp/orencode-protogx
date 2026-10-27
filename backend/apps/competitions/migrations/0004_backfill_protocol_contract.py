from django.db import migrations


REFERENCE_URL = "https://sudact.ru/law/pravila-vida-sporta-sportivnoe-programmirovanie-utv-prikazom/prilozhenie-n-5/rekomenduemyi-obrazets-protokola-po-programmirovaniiu/"


def backfill(apps, schema_editor):
    Competition = apps.get_model("competitions", "Competition")
    ProtocolTemplate = apps.get_model("competitions", "ProtocolTemplate")
    for competition in Competition.objects.filter(age_reference_date__isnull=True):
        competition.age_reference_date = competition.starts_at.date()
        competition.save(update_fields=["age_reference_date"])
    for template in ProtocolTemplate.objects.all():
        template.sections = template.sections or ["header", "participants", "judges", "signatures"]
        template.signature_roles = template.signature_roles or ["Главный судья", "Секретарь"]
        template.sort = template.sort or {"key": "place" if "place" in template.columns else "athlete", "direction": "asc"}
        template.source_url = template.source_url or REFERENCE_URL
        template.save(update_fields=["sections", "signature_roles", "sort", "source_url"])


class Migration(migrations.Migration):
    dependencies = [("competitions", "0003_competition_age_reference_date_and_more")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
