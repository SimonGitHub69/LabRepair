from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0028_configurazione_pc_pratica_tasti"),
    ]

    operations = [
        migrations.AddField(
            model_name="stampante",
            name="stampante_buste",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo, questa stampante viene usata per la stampa buste "
                    "di questa postazione (gap e selezione)."
                ),
                verbose_name="Stampante buste",
            ),
        ),
    ]
