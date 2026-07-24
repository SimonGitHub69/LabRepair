from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pratiche", "0036_pratica_prezzo_unita"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pratica",
            name="oro_aggiunto",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name="Peso aggiunto",
            ),
        ),
    ]
