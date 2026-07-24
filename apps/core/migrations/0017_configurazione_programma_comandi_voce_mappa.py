from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_configurazione_programma_voce_liste"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="comandi_voce_mappa",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Frasi personalizzate per azione. Se vuoto per un'azione, si usano i predefiniti."
                ),
                verbose_name="Mappa frasi comandi vocali",
            ),
        ),
    ]
