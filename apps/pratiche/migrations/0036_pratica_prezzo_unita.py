from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pratiche", "0035_tipooggetto_um_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="pratica",
            name="prezzo_unita",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name="Prezzo al",
            ),
        ),
    ]
