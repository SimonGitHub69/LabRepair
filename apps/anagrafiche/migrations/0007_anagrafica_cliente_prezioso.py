from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("anagrafiche", "0006_anagrafica_nome_cognome"),
    ]

    operations = [
        migrations.AddField(
            model_name="anagrafica",
            name="sesso",
            field=models.CharField(
                blank=True,
                choices=[("M", "M"), ("F", "F")],
                max_length=1,
                verbose_name="Sesso",
            ),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="data_nascita",
            field=models.DateField(blank=True, null=True, verbose_name="Data nascita"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="luogo_nascita",
            field=models.CharField(blank=True, max_length=100, verbose_name="Luogo nascita"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="provincia_nascita",
            field=models.CharField(blank=True, max_length=2, verbose_name="Prov. nascita"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="cellulare",
            field=models.CharField(blank=True, max_length=30, verbose_name="Cellulare"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="documento_tipo",
            field=models.CharField(blank=True, max_length=50, verbose_name="Tipo documento"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="documento_numero",
            field=models.CharField(blank=True, max_length=50, verbose_name="Numero documento"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="documento_rilasciato_da",
            field=models.CharField(blank=True, max_length=100, verbose_name="Rilasciato da"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="documento_comune_rilascio",
            field=models.CharField(blank=True, max_length=100, verbose_name="Comune rilascio"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="documento_provincia_rilascio",
            field=models.CharField(blank=True, max_length=2, verbose_name="Prov. rilascio"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="documento_data_rilascio",
            field=models.DateField(blank=True, null=True, verbose_name="Data rilascio"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="documento_data_scadenza",
            field=models.DateField(blank=True, null=True, verbose_name="Data scadenza"),
        ),
        migrations.AddField(
            model_name="anagrafica",
            name="stampa_privacy",
            field=models.BooleanField(default=False, verbose_name="Stampa privacy"),
        ),
    ]
