import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_negozi(apps, schema_editor):
    Negozio = apps.get_model("core", "Negozio")
    ConfigurazioneProgramma = apps.get_model("core", "ConfigurazioneProgramma")

    cfg = ConfigurazioneProgramma.objects.order_by("id").first()
    sezionale = "R"
    numero_iniziale = 1
    if cfg:
        sezionale = (getattr(cfg, "ddt_sezionale", None) or "R").strip().upper() or "R"
        try:
            numero_iniziale = max(1, int(getattr(cfg, "ddt_numero_iniziale", 1) or 1))
        except (TypeError, ValueError):
            numero_iniziale = 1

    defaults = (
        ("PT", "Pistoia", "P", "PISTOIA", 10),
        ("MO", "Montale", "M", "MONTALE", 20),
        ("QU", "Quarrata", "Q", "QUARRATA", 30),
    )
    for codice, denominazione, prefisso, localita, ordine in defaults:
        Negozio.objects.update_or_create(
            codice=codice,
            defaults={
                "denominazione": denominazione,
                "prefisso_pratica": prefisso,
                "localita_privacy": localita,
                "ordine": ordine,
                "ddt_sezionale": sezionale,
                "ddt_numero_iniziale": numero_iniziale,
                "is_active": True,
            },
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0037_ddt_progressivo_e_campi_busta"),
    ]

    operations = [
        migrations.CreateModel(
            name="Negozio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creato il")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modificato il")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Attivo")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
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
                    "codice",
                    models.CharField(
                        help_text="Sigla a 2 caratteri (es. PT, MO, QU).",
                        max_length=2,
                        unique=True,
                        verbose_name="Codice",
                    ),
                ),
                ("denominazione", models.CharField(max_length=100, verbose_name="Denominazione")),
                (
                    "prefisso_pratica",
                    models.CharField(
                        help_text="Lettera usata nei codici riparazione (es. P → P26-0001).",
                        max_length=1,
                        verbose_name="Prefisso codice riparazione",
                    ),
                ),
                (
                    "localita_privacy",
                    models.CharField(
                        blank=True,
                        help_text="Testo località nei documenti privacy (es. PISTOIA).",
                        max_length=100,
                        verbose_name="Località privacy",
                    ),
                ),
                ("ordine", models.PositiveIntegerField(default=0, verbose_name="Ordine")),
                (
                    "ddt_sezionale",
                    models.CharField(
                        blank=True,
                        default="R",
                        help_text="Suffisso numerazione DDT di questo negozio (es. R → 100/R).",
                        max_length=10,
                        verbose_name="Sezionale DDT",
                    ),
                ),
                (
                    "ddt_numero_iniziale",
                    models.PositiveIntegerField(
                        default=1,
                        help_text=(
                            "Primo numero DDT per questo negozio. I successivi partono dal massimo "
                            "esistente + 1 e non scendono sotto questo valore."
                        ),
                        verbose_name="Numerazione DDT iniziale",
                    ),
                ),
            ],
            options={
                "verbose_name": "Negozio",
                "verbose_name_plural": "Negozi",
                "ordering": ["ordine", "codice"],
            },
        ),
        migrations.RunPython(seed_negozi, noop_reverse),
    ]
