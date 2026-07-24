from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0038_parametri_access_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="pratica",
            name="senza_spesa",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, consente stato In consegna anche con Costo totale a zero.",
                verbose_name="Senza spesa",
            ),
        ),
    ]
