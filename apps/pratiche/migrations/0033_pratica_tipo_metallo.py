from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pratiche", "0032_pratica_prezzo_al_pubblico"),
    ]

    operations = [
        migrations.AddField(
            model_name="pratica",
            name="tipo_metallo",
            field=models.CharField(
                blank=True,
                choices=[
                    ("oro", "Oro"),
                    ("argento", "Argento"),
                    ("platino", "Platino"),
                ],
                max_length=20,
                verbose_name="Tipo di metallo",
            ),
        ),
    ]
