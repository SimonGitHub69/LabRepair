from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_configurazione_programma_webcam_tasti_extra"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="comunicazioni_mostra_allegato",
            field=models.BooleanField(
                default=True,
                help_text="Se disattivato, nasconde il campo file/webcam nel form comunicazioni.",
                verbose_name="Mostra mail o allegato nelle comunicazioni",
            ),
        ),
    ]
