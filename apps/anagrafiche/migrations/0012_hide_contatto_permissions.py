# Nasconde dai gruppi i permessi Contatto (residuo SECURTEK)

from django.db import migrations


def hide_contatto_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    cts = ContentType.objects.filter(app_label="anagrafiche", model="contatto")
    Permission.objects.filter(content_type__in=cts).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("anagrafiche", "0011_anagrafica_import_clienti_csv_permission"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="contatto",
            options={
                "default_permissions": (),
                "ordering": ["anagrafica__ragione_sociale", "-principale", "tipo", "valore"],
                "verbose_name": "Contatto",
                "verbose_name_plural": "Contatti",
            },
        ),
        migrations.RunPython(hide_contatto_permissions, migrations.RunPython.noop),
    ]
