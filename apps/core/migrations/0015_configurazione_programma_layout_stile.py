from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_parametri_access_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="layout_stile",
            field=models.CharField(
                choices=[("standard", "Grafica standard"), ("compatta", "Grafica compatta")],
                default="standard",
                help_text=(
                    "Standard: layout arioso attuale. "
                    "Compatta: stesse informazioni con meno spazi e meno scorrimento."
                ),
                max_length=20,
                verbose_name="Stile grafica maschera riparazioni",
            ),
        ),
    ]
