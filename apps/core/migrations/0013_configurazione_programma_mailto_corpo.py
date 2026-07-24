from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_configurazione_programma_mailto_oggetto"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="mailto_corpo",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Corpo precompilato nel client di posta dai filtri "
                    "Non ritirate / Ritardo lavorazione. "
                    "Segnaposto: {codice}, {cliente}, {nome}, {cognome}, {cellulare}, {telefono}."
                ),
                verbose_name="Testo mail da elenco riparazioni",
            ),
        ),
    ]
