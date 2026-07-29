from django.db import migrations, models
import django.db.models.deletion


def collega_stampanti_a_postazioni(apps, schema_editor):
    ConfigurazionePC = apps.get_model("core", "ConfigurazionePC")
    Stampante = apps.get_model("core", "Stampante")

    for postazione in ConfigurazionePC.objects.filter(is_active=True):
        nomi = postazione.stampanti or []
        if isinstance(nomi, str):
            continue
        for nome in nomi:
            testo = str(nome or "").strip()
            if not testo:
                continue
            stampante = (
                Stampante.objects.filter(is_active=True, nome__iexact=testo, configurazione_pc__isnull=True)
                .order_by("id")
                .first()
            )
            if stampante is None:
                stampante = (
                    Stampante.objects.filter(nome__iexact=testo, configurazione_pc__isnull=True)
                    .order_by("-is_active", "id")
                    .first()
                )
            if stampante is None:
                Stampante.objects.create(
                    configurazione_pc=postazione,
                    nome=testo,
                    is_active=True,
                )
                continue
            stampante.configurazione_pc = postazione
            stampante.is_active = True
            stampante.deleted_at = None
            stampante.deleted_by = None
            stampante.save(
                update_fields=[
                    "configurazione_pc",
                    "is_active",
                    "deleted_at",
                    "deleted_by",
                    "updated_at",
                ]
            )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_stampante"),
    ]

    operations = [
        migrations.AddField(
            model_name="stampante",
            name="configurazione_pc",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="stampanti_collegate",
                to="core.configurazionepc",
                verbose_name="Postazione PC",
            ),
        ),
        migrations.RunPython(collega_stampanti_a_postazioni, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="stampante",
            constraint=models.UniqueConstraint(
                fields=("configurazione_pc", "nome"),
                name="core_stampante_unique_per_pc",
            ),
        ),
    ]
