from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_alter_configurazionemssql_iva_id_cassa_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionepc",
            name="busta_stampa_senza_anteprima",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo, da questa postazione la stampa busta apre subito "
                    "la finestra di stampa senza mostrare l'anteprima a schermo."
                ),
                verbose_name="Stampa busta senza anteprima",
            ),
        ),
    ]
