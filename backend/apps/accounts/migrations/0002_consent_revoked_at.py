from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [
        migrations.AddField(model_name="personaldataconsent", name="revoked_at", field=models.DateTimeField(blank=True, null=True)),
    ]
