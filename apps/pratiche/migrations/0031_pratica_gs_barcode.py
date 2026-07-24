from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0030_pratica_data_prevista_consegna_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="pratica",
            name="gs_barcode",
            field=models.DecimalField(
                blank=True,
                decimal_places=0,
                help_text="Barcode assegnato in GS_ARTICOLI sul gestionale SQL.",
                max_digits=10,
                null=True,
                unique=True,
                verbose_name="Barcode GS",
            ),
        ),
    ]
