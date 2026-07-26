# Aggiorna etichetta permesso Documenti nei privilegi gruppo

from django.db import migrations


def rename_accesso_menu_verbose(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    ct = ContentType.objects.filter(app_label="dashboard", model="accessomenu").first()
    if not ct:
        return
    Permission.objects.filter(content_type=ct, codename="access_documenti").update(
        name="Può accedere al menu Documenti"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0001_accesso_menu_documenti"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="accessomenu",
            options={
                "default_permissions": (),
                "permissions": [
                    ("access_documenti", "Può accedere al menu Documenti"),
                ],
                "verbose_name": "Documenti",
                "verbose_name_plural": "Documenti",
            },
        ),
        migrations.RunPython(rename_accesso_menu_verbose, migrations.RunPython.noop),
    ]
