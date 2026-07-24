from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_configurazione_programma_barcode_iniziale"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="webcam_tasto_scatto",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Disabilitato"),
                    ("F1", "F1"),
                    ("F2", "F2"),
                    ("F3", "F3"),
                    ("F4", "F4"),
                    ("F5", "F5"),
                    ("F6", "F6"),
                    ("F7", "F7"),
                    ("F8", "F8"),
                    ("F9", "F9"),
                    ("F10", "F10"),
                    ("F11", "F11"),
                    ("F12", "F12"),
                ],
                default="",
                help_text="Tasto funzione per aprire la webcam e scattare una foto.",
                max_length=3,
                verbose_name="Tasto scatto webcam",
            ),
        ),
    ]
