from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_configurazione_programma_comunicazioni_formato_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="privacy_testo_diritti",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Testo in calce alla scheda Privacy per l'esercizio dei diritti GDPR (art. 7). "
                    "Se vuoto, viene generato automaticamente dai dati azienda."
                ),
                verbose_name="Testo diritti privacy",
            ),
        ),
    ]
