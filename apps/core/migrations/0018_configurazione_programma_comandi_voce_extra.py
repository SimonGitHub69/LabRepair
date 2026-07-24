from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_configurazione_programma_comandi_voce_mappa"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="comandi_voce_extra",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Comandi aggiuntivi definiti dall'utente (frasi → destinazione).",
                verbose_name="Comandi vocali personalizzati",
            ),
        ),
    ]
