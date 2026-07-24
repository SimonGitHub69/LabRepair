import uuid

import django.db.models.deletion
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


def reset_barcode_prima_modalita(apps, schema_editor):
    ConfigurazioneProgramma = apps.get_model("core", "ConfigurazioneProgramma")
    ConfigurazioneProgramma.objects.filter(modalita_accettazione="barcode_prima").update(
        modalita_accettazione="standard"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_configurazione_programma"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(reset_barcode_prima_modalita, migrations.RunPython.noop),
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="barcode_iniziale",
            field=models.PositiveIntegerField(
                default=500000,
                help_text="Primo numero barcode GS assegnato alle riparazioni. I successivi partono dal massimo esistente + 1 in questa fascia.",
                validators=[
                    MinValueValidator(1),
                    MaxValueValidator(89999999),
                ],
                verbose_name="Numerazione barcode iniziale",
            ),
        ),
        migrations.AlterField(
            model_name="configurazioneprogramma",
            name="modalita_accettazione",
            field=models.CharField(
                choices=[
                    ("standard", "Standard (cliente per primo)"),
                    ("operatore_prima", "Operatore per primo"),
                ],
                default="standard",
                help_text="Standard: il form Nuova riparazione inizia dal cliente. Operatore per primo: il primo campo è l'operatore.",
                max_length=30,
                verbose_name="Modalità accettazione riparazione",
            ),
        ),
    ]
