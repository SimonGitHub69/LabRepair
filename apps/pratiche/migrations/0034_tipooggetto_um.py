from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pratiche", "0033_pratica_tipo_metallo"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipooggetto",
            name="um",
            field=models.CharField(
                blank=True,
                choices=[("ct", "ct"), ("gr", "gr")],
                max_length=2,
                verbose_name="UM",
            ),
        ),
    ]
