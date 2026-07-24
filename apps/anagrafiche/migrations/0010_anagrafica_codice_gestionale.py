from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("anagrafiche", "0009_anagrafica_documento_tipo_free_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="anagrafica",
            name="codice_gestionale",
            field=models.CharField(
                blank=True,
                help_text="Codice cliente sul gestionale (GS_ARTICOLI.CODCLIENTE, 7 caratteri).",
                max_length=7,
                verbose_name="Codice gestionale",
            ),
        ),
    ]
