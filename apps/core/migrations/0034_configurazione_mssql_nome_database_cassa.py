from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0033_configurazione_pc_layout_alto_contrasto"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionemssql",
            name="nome_database_cassa",
            field=models.CharField(
                blank=True,
                help_text="Database usato per la lettura degli scontrini.",
                max_length=200,
                verbose_name="Database Cassa",
            ),
        ),
        migrations.AlterField(
            model_name="configurazionemssql",
            name="nome_database",
            field=models.CharField(
                blank=True,
                help_text="Database per la sincronizzazione prezzi cassa (TB_PREZZICASSE).",
                max_length=200,
                verbose_name="Database",
            ),
        ),
    ]
