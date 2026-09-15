from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0032_configurazione_pc_busta_stampa_opzioni"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionepc",
            name="layout_alto_contrasto",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo, in Anagrafiche e Riparazioni aumenta contrasto e dimensione testo "
                    "ed evidenzia in blu grassetto i valori inseriti. Non modifica le altre sezioni."
                ),
                verbose_name="Grafica ad alto contrasto",
            ),
        ),
    ]
