"""Enforce inclusive effective-date overlap rules even for direct SQL/ORM writes.

Existing invalid data causes migration failure instead of being silently changed.
SQLite is supported for development but cannot enforce exclusion constraints.
"""
from django.db import migrations


TABLES = {
    "participationperiod": False,
    "organizationperiod": False,
    "municipalityperiod": False,
    "trainingstageperiod": False,
    "disciplineperiod": True,
}


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    for model, scoped_discipline in TABLES.items():
        discipline = ", discipline_id WITH =" if scoped_discipline else ""
        schema_editor.execute(
            f"ALTER TABLE registry_{model} ADD CONSTRAINT registry_{model}_no_overlap "
            f"EXCLUDE USING gist (athlete_id WITH ={discipline}, daterange(starts_on, ends_on, '[]') WITH &&)"
        )


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for model in TABLES:
        schema_editor.execute(f"ALTER TABLE registry_{model} DROP CONSTRAINT registry_{model}_no_overlap")
    # btree_gist may be shared by other applications; never drop the extension.


class Migration(migrations.Migration):
    dependencies = [("registry", "0001_initial")]
    operations = [migrations.RunPython(install, uninstall)]
