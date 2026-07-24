import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_azienda"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfigurazioneMssql",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creato il")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modificato il")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il")),
                ("is_active", models.BooleanField(default=True, verbose_name="Attivo")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
                ("attiva", models.BooleanField(default=False, verbose_name="Attiva")),
                ("server", models.CharField(blank=True, max_length=300, verbose_name="Istanza server")),
                ("porta", models.PositiveIntegerField(default=1433, verbose_name="Porta")),
                ("nome_database", models.CharField(blank=True, max_length=200, verbose_name="Database")),
                ("utente", models.CharField(blank=True, max_length=200, verbose_name="Utente")),
                ("password", models.CharField(blank=True, max_length=200, verbose_name="Password")),
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
                "verbose_name": "Configurazione MS-SQL",
                "verbose_name_plural": "Configurazioni MS-SQL",
            },
        ),
    ]
