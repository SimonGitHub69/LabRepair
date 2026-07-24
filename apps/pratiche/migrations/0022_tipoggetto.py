import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


DEFAULT_TIPI_OGGETTO = [
    "altro",
    "anello",
    "bracciale",
    "catena",
    "cavigliera",
    "ciondolo",
    "collana infilata",
    "fermatura",
    "girocollo",
    "orecchini",
    "orologio",
    "orologio da parete",
    "pietra",
    "spilla",
    "sveglia",
]


def populate_tipi_oggetto(apps, schema_editor):
    TipoOggetto = apps.get_model("pratiche", "TipoOggetto")
    for denominazione in DEFAULT_TIPI_OGGETTO:
        TipoOggetto.objects.get_or_create(denominazione=denominazione)


def migrate_pratica_tipo_oggetto(apps, schema_editor):
    TipoOggetto = apps.get_model("pratiche", "TipoOggetto")
    Pratica = apps.get_model("pratiche", "Pratica")

    tipi = {
        tipo.denominazione.lower(): tipo
        for tipo in TipoOggetto.objects.all()
    }

    for pratica in Pratica.objects.exclude(tipo_oggetto_legacy=""):
        legacy_value = (pratica.tipo_oggetto_legacy or "").strip()
        if not legacy_value:
            continue

        tipo = tipi.get(legacy_value.lower())
        if tipo is None:
            tipo, _ = TipoOggetto.objects.get_or_create(denominazione=legacy_value)
            tipi[legacy_value.lower()] = tipo

        pratica.tipo_oggetto = tipo
        pratica.save(update_fields=["tipo_oggetto"])


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0021_alter_pratica_responsabile_operatore_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TipoOggetto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creato il")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modificato il")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il")),
                ("is_active", models.BooleanField(default=True, verbose_name="Attivo")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
                ("denominazione", models.CharField(max_length=120, unique=True, verbose_name="Denominazione")),
                ("descrizione", models.TextField(blank=True, verbose_name="Descrizione")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creato da",
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Eliminato da",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Modificato da",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tipo oggetto",
                "verbose_name_plural": "Tipi di oggetto",
                "ordering": ["denominazione"],
            },
        ),
        migrations.RunPython(populate_tipi_oggetto, migrations.RunPython.noop),
        migrations.RenameField(
            model_name="pratica",
            old_name="tipo_oggetto",
            new_name="tipo_oggetto_legacy",
        ),
        migrations.AddField(
            model_name="pratica",
            name="tipo_oggetto",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pratiche",
                to="pratiche.tipooggetto",
                verbose_name="Tipo oggetto",
            ),
        ),
        migrations.RunPython(migrate_pratica_tipo_oggetto, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="pratica",
            name="tipo_oggetto_legacy",
        ),
    ]
