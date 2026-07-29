from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_stampante_configurazione_pc"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionemssql",
            name="prz_pvn_codice",
            field=models.CharField(
                blank=True,
                default="TN",
                help_text="Valore PRZ_PVN_CODICE su TB_PREZZICASSE (in 4D tipicamente TN).",
                max_length=10,
                verbose_name="Codice PVN casse",
            ),
        ),
        migrations.AddField(
            model_name="configurazionemssql",
            name="iva_id_cassa",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="PRZ_IVA_ID (da TabAliquoteIva.ID_IVA_CASSA / CODIVAMETODO).",
                null=True,
                verbose_name="ID IVA casse",
            ),
        ),
        migrations.AddField(
            model_name="configurazionemssql",
            name="iva_aliquota_cassa",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("22.00"),
                help_text="PRZ_IVA_ALIQUOTA (es. 22.00).",
                max_digits=5,
                verbose_name="Aliquota IVA casse",
            ),
        ),
    ]
