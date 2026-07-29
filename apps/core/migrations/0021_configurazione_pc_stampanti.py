from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_alter_configurazioneprogramma_layout_stile"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionepc",
            name="stampanti",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Stampanti Windows associate a questa postazione.",
                verbose_name="Stampanti",
            ),
        ),
    ]
