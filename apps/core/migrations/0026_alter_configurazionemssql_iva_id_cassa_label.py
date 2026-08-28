from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0025_configurazione_mssql_iva_id_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="configurazionemssql",
            name="iva_id_cassa",
            field=models.PositiveIntegerField(
                blank=True,
                default=10,
                help_text="Valore PRZ_IVA_ID su TB_PREZZICASSE (default 10).",
                null=True,
                verbose_name="ID_IVA_CASSA",
            ),
        ),
    ]
