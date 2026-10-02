from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0046_ddt_negozio_numerazione"),
    ]

    operations = [
        migrations.AddField(
            model_name="pratica",
            name="numero_scontrino",
            field=models.CharField(
                blank=True,
                help_text="Numero scontrino letto da Database Cassa (GS_VENDITE_DETTAGLIO.NUM_SCONTRINO).",
                max_length=30,
                verbose_name="N. scontrino",
            ),
        ),
    ]
