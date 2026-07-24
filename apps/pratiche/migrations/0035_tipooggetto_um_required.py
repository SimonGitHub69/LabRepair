from django.db import migrations, models


def fill_missing_um(apps, schema_editor):
    TipoOggetto = apps.get_model("pratiche", "TipoOggetto")
    TipoOggetto.objects.filter(um="").update(um="gr")


class Migration(migrations.Migration):
    dependencies = [
        ("pratiche", "0034_tipooggetto_um"),
    ]

    operations = [
        migrations.RunPython(fill_missing_um, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="tipooggetto",
            name="um",
            field=models.CharField(
                choices=[("ct", "ct"), ("gr", "gr")],
                max_length=2,
                verbose_name="UM",
            ),
        ),
    ]
