from decimal import Decimal

import django.db.models.deletion
import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0021_configurazione_pc_stampanti"),
    ]

    operations = [
        migrations.CreateModel(
            name="Stampante",
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
                    "nome",
                    models.CharField(
                        db_index=True,
                        help_text="Nome Windows della stampante rilevata sul sistema.",
                        max_length=200,
                        verbose_name="Nome stampante",
                    ),
                ),
                (
                    "descrizione",
                    models.CharField(
                        blank=True,
                        help_text="Descrizione libera (es. stampante buste cassa 1).",
                        max_length=255,
                        verbose_name="Descrizione",
                    ),
                ),
                (
                    "gap_busta_superiore",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="Spazio superiore busta in mm (due decimali).",
                        max_digits=8,
                        validators=[MinValueValidator(Decimal("0.00"))],
                        verbose_name="Gap busta superiore",
                    ),
                ),
                (
                    "gap_busta_inferiore",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="Spazio inferiore busta in mm (due decimali).",
                        max_digits=8,
                        validators=[MinValueValidator(Decimal("0.00"))],
                        verbose_name="Gap busta inferiore",
                    ),
                ),
                ("porta", models.CharField(blank=True, max_length=200, verbose_name="Porta")),
                ("driver", models.CharField(blank=True, max_length=200, verbose_name="Driver")),
                (
                    "predefinita",
                    models.BooleanField(default=False, verbose_name="Predefinita di sistema"),
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
                        verbose_name="Aggiornato da",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stampante",
                "verbose_name_plural": "Stampanti",
                "ordering": ["nome"],
            },
        ),
    ]
