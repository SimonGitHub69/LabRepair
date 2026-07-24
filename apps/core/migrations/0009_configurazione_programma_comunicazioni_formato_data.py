from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_configurazione_programma_comunicazioni_allegato"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="comunicazioni_formato_data",
            field=models.CharField(
                choices=[
                    ("data_ora", "Data e ora"),
                    ("solo_data", "Solo data"),
                    ("nascosto", "Non mostrare (usa data/ora corrente)"),
                ],
                default="data_ora",
                help_text="Formato del campo data nel form comunicazioni della scheda riparazione.",
                max_length=20,
                verbose_name="Campo data comunicazioni",
            ),
        ),
    ]
