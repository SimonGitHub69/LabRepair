# Generated manually for ConfigurazionePC

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0018_configurazione_programma_comandi_voce_extra"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfigurazionePC",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                        verbose_name="UUID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Creato il"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Modificato il"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il"),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Attivo")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
                (
                    "nome_pc",
                    models.CharField(
                        db_index=True,
                        help_text="Nome fisico del computer (es. DESKTOP-PISTOIA01).",
                        max_length=100,
                        verbose_name="Nome PC",
                    ),
                ),
                (
                    "descrizione",
                    models.CharField(
                        blank=True,
                        help_text="Etichetta aggiuntiva per riconoscere la postazione.",
                        max_length=200,
                        verbose_name="Descrizione",
                    ),
                ),
                (
                    "negozio_default",
                    models.CharField(
                        choices=[
                            ("PT", "Pistoia"),
                            ("MO", "Montale"),
                            ("QU", "Quarrata"),
                        ],
                        help_text="Negozio proposto al login da questo PC.",
                        max_length=2,
                        verbose_name="Negozio predefinito",
                    ),
                ),
                (
                    "layout_stile",
                    models.CharField(
                        choices=[
                            ("standard", "Grafica standard"),
                            ("compatta", "Grafica compatta"),
                        ],
                        default="standard",
                        help_text=(
                            "Interfaccia usata da questa postazione "
                            "(sovrascrive Parametri programma)."
                        ),
                        max_length=20,
                        verbose_name="Stile grafica",
                    ),
                ),
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
                "verbose_name": "Configurazione PC",
                "verbose_name_plural": "Configurazioni PC",
                "ordering": ["nome_pc"],
            },
        ),
    ]
