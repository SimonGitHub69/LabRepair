from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0047_pratica_numero_scontrino"),
    ]

    operations = [
        migrations.AddField(
            model_name="pratica",
            name="busta_stampata_il",
            field=models.DateTimeField(
                blank=True,
                help_text="Se valorizzata, il cliente della riparazione non è più modificabile.",
                null=True,
                verbose_name="Busta stampata il",
            ),
        ),
    ]
