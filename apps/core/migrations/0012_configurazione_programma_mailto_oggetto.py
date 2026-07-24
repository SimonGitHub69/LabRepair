from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_configurazione_programma_privacy_dichiarazione"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="mailto_oggetto",
            field=models.CharField(
                blank=True,
                default="Riparazione {codice} - {cliente}",
                help_text=(
                    "Oggetto precompilato quando si apre il client di posta dai filtri "
                    "Non ritirate / Ritardo lavorazione. "
                    "Segnaposto: {codice}, {cliente}, {nome}, {cognome}."
                ),
                max_length=200,
                verbose_name="Oggetto mail da elenco riparazioni",
            ),
        ),
    ]
