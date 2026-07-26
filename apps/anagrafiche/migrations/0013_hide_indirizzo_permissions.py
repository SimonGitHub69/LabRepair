# Nasconde Contatto/Indirizzo dai privilegi gruppo (residui SECURTEK)

from django.db import migrations


def hide_contatto_indirizzo_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    cts = ContentType.objects.filter(
        app_label="anagrafiche",
        model__in=["contatto", "indirizzo"],
    )
    Permission.objects.filter(content_type__in=cts).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("anagrafiche", "0012_hide_contatto_permissions"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="indirizzo",
            options={
                "default_permissions": (),
                "ordering": ["anagrafica__ragione_sociale", "-principale", "tipo"],
                "verbose_name": "Indirizzo",
                "verbose_name_plural": "Indirizzi",
            },
        ),
        migrations.RunPython(
            hide_contatto_indirizzo_permissions,
            migrations.RunPython.noop,
        ),
    ]
