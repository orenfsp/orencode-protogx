import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("qualifications", "0001_initial"), ("competitions", "0005_protocoltemplate_competition_type_and_more")]
    operations = [
        migrations.AddField(model_name="rankapplication", name="publication", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="rank_applications", to="competitions.protocolpublication")),
        migrations.AddField(model_name="rankapplication", name="result_snapshot", field=models.JSONField(blank=True, null=True)),
    ]
