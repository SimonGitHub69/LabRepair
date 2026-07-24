from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_configurazione_programma_webcam_tasto"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="webcam_tasto_nuovo_scatto",
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
                help_text="Scarta l'anteprima e prepara un nuovo scatto.",
                max_length=3,
                verbose_name="Tasto nuovo scatto",
            ),
        ),
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="webcam_tasto_usa_foto",
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
                help_text="Conferma e usa la foto appena scattata.",
                max_length=3,
                verbose_name="Tasto usa foto",
            ),
        ),
        migrations.AlterField(
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
                help_text="Apre la webcam oppure scatta una foto con il modale già aperto.",
                max_length=3,
                verbose_name="Tasto scatto foto",
            ),
        ),
    ]
