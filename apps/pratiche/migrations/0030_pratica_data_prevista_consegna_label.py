from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0029_pratica_foto"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pratica",
            name="data_scadenza",
            field=models.DateField(blank=True, null=True, verbose_name="Data prevista consegna"),
        ),
    ]
