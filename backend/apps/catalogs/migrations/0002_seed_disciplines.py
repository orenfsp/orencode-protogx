from django.db import migrations


DISCIPLINES = [
    ("algorithmic", "Программирование алгоритмическое"),
    ("product", "Программирование продуктовое"),
    ("security", "Программирование систем информационной безопасности"),
    ("ai", "Программирование систем искусственного интеллекта"),
    ("robotics", "Программирование робототехники"),
    ("uav", "Программирование беспилотных авиационных систем"),
]


def seed(apps, schema_editor):
    Discipline = apps.get_model("catalogs", "Discipline")
    for code, name in DISCIPLINES:
        Discipline.objects.get_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("catalogs", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
