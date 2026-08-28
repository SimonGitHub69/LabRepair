from decimal import Decimal

from django.db import migrations, models


def set_default_iva_id(apps, schema_editor):
    ConfigurazioneMssql = apps.get_model("core", "ConfigurazioneMssql")
    ConfigurazioneMssql.objects.filter(iva_id_cassa__isnull=True).update(iva_id_cassa=10)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_configurazione_mssql_prezzi_casse"),
    ]

    operations = [
        migrations.AlterField(
            model_name="configurazionemssql",
            name="iva_id_cassa",
            field=models.PositiveIntegerField(
                blank=True,
                default=10,
                help_text="PRZ_IVA_ID (da TabAliquoteIva.ID_IVA_CASSA / CODIVAMETODO). Default: 10.",
                null=True,
                verbose_name="ID IVA casse",
            ),
        ),
        migrations.RunPython(set_default_iva_id, migrations.RunPython.noop),
    ]
