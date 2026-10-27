from django.db import migrations


METRICS = {
    "algorithmic": ("solved_tasks", "Решено задач", "number"),
    "product": ("project_note", "Описание продукта", "string"),
    "security": ("security_note", "Описание задания", "string"),
    "ai": ("model_note", "Описание модели", "string"),
    "robotics": ("robot_note", "Описание робота", "string"),
    "uav": ("flight_note", "Описание полёта", "string"),
}


def seed(apps, schema_editor):
    AgeGroup = apps.get_model("competitions", "AgeGroup")
    Discipline = apps.get_model("catalogs", "Discipline")
    ProtocolTemplate = apps.get_model("competitions", "ProtocolTemplate")
    AgeGroup.objects.get_or_create(name="Демо: 12–17 лет", defaults={"min_age": 12, "max_age": 17})
    AgeGroup.objects.get_or_create(name="Демо: 18+", defaults={"min_age": 18, "max_age": 99})
    for code, (key, label, kind) in METRICS.items():
        discipline = Discipline.objects.get(code=code)
        ProtocolTemplate.objects.get_or_create(
            discipline=discipline,
            version=1,
            defaults={
                "name": f"Демо-шаблон: {discipline.name}",
                "metric_fields": [{"key": key, "label": label, "type": kind, "required": False}],
                "columns": ["athlete", "age_group", "status", "place", "score", key],
                "source_verified": False,
                "source_note": "Демо-структура; перед официальным использованием сверить с действующими правилами и первоисточником приложения № 5.",
            },
        )


class Migration(migrations.Migration):
    dependencies = [("competitions", "0001_initial"), ("catalogs", "0002_seed_disciplines")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
