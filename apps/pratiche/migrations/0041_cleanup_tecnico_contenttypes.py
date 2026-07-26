# Generated manually for LabRepair — pulizia permessi Tecnico/Incarico

from django.db import migrations


def remove_stale_tecnico_contenttypes(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(
        app_label="pratiche",
        model__in=["tecnico", "incaricotecnico"],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0040_remove_tecnico_incaricotecnico"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(remove_stale_tecnico_contenttypes, migrations.RunPython.noop),
    ]
