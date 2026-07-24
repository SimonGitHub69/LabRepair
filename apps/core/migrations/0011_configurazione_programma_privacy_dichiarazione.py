from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_configurazione_programma_privacy_testo"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="privacy_testo_dichiarazione",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Dichiarazione del sottoscritto sulla provenienza e sui diritti degli oggetti "
                    "nella scheda Privacy. Se vuoto, viene usato il testo predefinito."
                ),
                verbose_name="Testo dichiarazione provenienza",
            ),
        ),
    ]
