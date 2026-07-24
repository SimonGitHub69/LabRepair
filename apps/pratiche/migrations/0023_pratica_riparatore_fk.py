import django.db.models.deletion
from django.db import migrations, models


def migrate_pratica_riparatore(apps, schema_editor):
    StudioTecnico = apps.get_model("pratiche", "StudioTecnico")
    Pratica = apps.get_model("pratiche", "Pratica")

    studi = {
        studio.denominazione.lower(): studio
        for studio in StudioTecnico.objects.all()
    }

    for pratica in Pratica.objects.exclude(riparatore_legacy=""):
        legacy_value = (pratica.riparatore_legacy or "").strip()
        if not legacy_value:
            continue

        studio = studi.get(legacy_value.lower())
        if studio is None:
            studio, _ = StudioTecnico.objects.get_or_create(denominazione=legacy_value)
            studi[legacy_value.lower()] = studio

        pratica.riparatore = studio
        pratica.save(update_fields=["riparatore"])


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0022_tipoggetto"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="studiotecnico",
            options={
                "ordering": ["denominazione"],
                "verbose_name": "Riparatore",
                "verbose_name_plural": "Riparatori",
            },
        ),
        migrations.RenameField(
            model_name="pratica",
            old_name="riparatore",
            new_name="riparatore_legacy",
        ),
        migrations.AddField(
            model_name="pratica",
            name="riparatore",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pratiche_riparazione",
                to="pratiche.studiotecnico",
                verbose_name="Riparatore",
            ),
        ),
        migrations.RunPython(migrate_pratica_riparatore, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="pratica",
            name="riparatore_legacy",
        ),
    ]
