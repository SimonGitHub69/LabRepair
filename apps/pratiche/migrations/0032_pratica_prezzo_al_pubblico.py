from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pratiche", "0031_pratica_gs_barcode"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pratica",
            name="prezzo_al",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name="Prezzo al Pubblico",
            ),
        ),
    ]
