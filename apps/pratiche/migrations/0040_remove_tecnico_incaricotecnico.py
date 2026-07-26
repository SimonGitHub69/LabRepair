# Generated manually for LabRepair — rimozione residui SECURTEK

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0039_pratica_senza_spesa"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Tecnico",
        ),
        migrations.DeleteModel(
            name="IncaricoTecnico",
        ),
    ]
