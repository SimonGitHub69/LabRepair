from django.db import migrations


def ensure_menu_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    ct, _ = ContentType.objects.get_or_create(app_label="dashboard", model="accessomenu")
    wanted = {
        "access_documenti": "Può accedere al menu Documenti",
        "access_report": "Può accedere al menu Report",
        "access_comandi_vocali": "Può accedere al menu Comandi vocali",
    }
    for codename, name in wanted.items():
        Permission.objects.update_or_create(
            content_type=ct,
            codename=codename,
            defaults={"name": name},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0002_documenti_permission_label"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="accessomenu",
            options={
                "default_permissions": (),
                "permissions": [
                    ("access_documenti", "Può accedere al menu Documenti"),
                    ("access_report", "Può accedere al menu Report"),
                    ("access_comandi_vocali", "Può accedere al menu Comandi vocali"),
                ],
                "verbose_name": "Accesso menu",
                "verbose_name_plural": "Accessi menu",
            },
        ),
        migrations.RunPython(ensure_menu_permissions, migrations.RunPython.noop),
    ]
