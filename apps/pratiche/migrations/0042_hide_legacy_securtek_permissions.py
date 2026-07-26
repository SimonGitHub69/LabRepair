# Residui SECURTEK: niente permessi standard nei gruppi LabRepair

from django.db import migrations


LEGACY_MODELS = (
    "categoriapratica",
    "macrocategoriapratica",
    "templatepratica",
    "praticacategoria",
    "praticamacrocategoria",
    "praticacategoriafile",
    "praticacategoriaallegato",
    # eventuali residui Tecnico/Incarico non ancora migrati sul cliente
    "tecnico",
    "incaricotecnico",
)


def hide_legacy_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    cts = ContentType.objects.filter(app_label="pratiche", model__in=LEGACY_MODELS)
    Permission.objects.filter(content_type__in=cts).delete()
    # Rimuove anche ContentType orfani di modelli gia' cancellati
    ContentType.objects.filter(
        app_label="pratiche",
        model__in=("tecnico", "incaricotecnico"),
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0041_cleanup_tecnico_contenttypes"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="categoriapratica",
            options={
                "default_permissions": (),
                "ordering": ["denominazione"],
                "verbose_name": "Categoria riparazione",
                "verbose_name_plural": "Categorie riparazioni",
            },
        ),
        migrations.AlterModelOptions(
            name="macrocategoriapratica",
            options={
                "default_permissions": (),
                "ordering": ["denominazione"],
                "verbose_name": "Macro-categoria riparazione",
                "verbose_name_plural": "Macro-categorie riparazioni",
            },
        ),
        migrations.AlterModelOptions(
            name="templatepratica",
            options={
                "default_permissions": (),
                "ordering": ["tipologia"],
                "verbose_name": "Template riparazione",
                "verbose_name_plural": "Template riparazioni",
            },
        ),
        migrations.AlterModelOptions(
            name="praticacategoria",
            options={
                "default_permissions": (),
                "ordering": [
                    "macro_categoria__denominazione",
                    "categoria__denominazione",
                    "versione",
                ],
                "verbose_name": "Categoria riparazione collegata",
                "verbose_name_plural": "Categorie riparazione collegate",
            },
        ),
        migrations.AlterModelOptions(
            name="praticamacrocategoria",
            options={
                "default_permissions": (),
                "ordering": ["macro_categoria__denominazione"],
                "verbose_name": "Macro-categoria riparazione collegata",
                "verbose_name_plural": "Macro-categorie riparazione collegate",
            },
        ),
        migrations.AlterModelOptions(
            name="praticacategoriafile",
            options={
                "default_permissions": (),
                "ordering": ["percorso_relativo"],
                "verbose_name": "File categoria riparazione",
                "verbose_name_plural": "File categorie riparazione",
            },
        ),
        migrations.AlterModelOptions(
            name="praticacategoriaallegato",
            options={
                "default_permissions": (),
                "ordering": ["file"],
                "verbose_name": "Allegato singolo categoria riparazione",
                "verbose_name_plural": "Allegati singoli categorie riparazione",
            },
        ),
        migrations.RunPython(hide_legacy_permissions, migrations.RunPython.noop),
    ]
