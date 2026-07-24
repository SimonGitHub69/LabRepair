import apps.pratiche.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def migrate_foto_oggetto_to_pratica_foto(apps, schema_editor):
    Pratica = apps.get_model("pratiche", "Pratica")
    PraticaFoto = apps.get_model("pratiche", "PraticaFoto")

    for pratica in Pratica.objects.exclude(foto_oggetto="").exclude(foto_oggetto__isnull=True):
        if not pratica.foto_oggetto:
            continue

        foto = PraticaFoto(
            pratica_id=pratica.pk,
            is_active=True,
        )
        foto.immagine.name = pratica.foto_oggetto.name
        foto.save()


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0028_pratica_foto_oggetto"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PraticaFoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creato il")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modificato il")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il")),
                ("is_active", models.BooleanField(default=True, verbose_name="Attivo")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
                (
                    "immagine",
                    models.FileField(
                        max_length=500,
                        upload_to=apps.pratiche.models.pratica_foto_upload_to,
                        verbose_name="Immagine",
                    ),
                ),
                ("didascalia", models.CharField(blank=True, max_length=200, verbose_name="Didascalia")),
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
                    "pratica",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="foto",
                        to="pratiche.pratica",
                        verbose_name="Riparazione",
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
                "verbose_name": "Foto riparazione",
                "verbose_name_plural": "Foto riparazioni",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.RunPython(migrate_foto_oggetto_to_pratica_foto, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="pratica",
            name="foto_oggetto",
        ),
    ]
