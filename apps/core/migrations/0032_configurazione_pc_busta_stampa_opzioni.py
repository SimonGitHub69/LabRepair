from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0031_sync_field_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionepc",
            name="busta_stampa_salva_scheda",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Se attivo, prima di stampare la busta viene salvata la scheda riparazione. "
                    "Se disattivo, la busta usa i dati già registrati."
                ),
                verbose_name="Salva scheda prima di stampare la busta",
            ),
        ),
        migrations.AddField(
            model_name="configurazionepc",
            name="busta_stampa_torna_elenco",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo, dopo la stampa busta si torna all'elenco riparazioni. "
                    "Se disattivo, si resta nella scheda."
                ),
                verbose_name="Torna all'elenco dopo la stampa busta",
            ),
        ),
    ]
