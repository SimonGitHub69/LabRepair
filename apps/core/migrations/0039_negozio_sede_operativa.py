from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0038_negozio"),
    ]

    operations = [
        migrations.AddField(
            model_name="negozio",
            name="indirizzo",
            field=models.CharField(blank=True, max_length=255, verbose_name="Indirizzo"),
        ),
        migrations.AddField(
            model_name="negozio",
            name="civico",
            field=models.CharField(blank=True, max_length=20, verbose_name="Civico"),
        ),
        migrations.AddField(
            model_name="negozio",
            name="cap",
            field=models.CharField(blank=True, max_length=10, verbose_name="CAP"),
        ),
        migrations.AddField(
            model_name="negozio",
            name="comune",
            field=models.CharField(blank=True, max_length=100, verbose_name="Comune"),
        ),
        migrations.AddField(
            model_name="negozio",
            name="provincia",
            field=models.CharField(blank=True, max_length=2, verbose_name="Provincia"),
        ),
    ]
