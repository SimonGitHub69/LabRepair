from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_stampante_stampante_buste"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionepc",
            name="pratica_stato_radio",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo, nella maschera riparazione lo Stato si seleziona "
                    "con radio-bottoni (Accettazione, Riparatore, In consegna, …) "
                    "al posto del menu a tendina."
                ),
                verbose_name="Stato riparazione a radio-bottoni",
            ),
        ),
    ]
