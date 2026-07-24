from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_configurazione_mssql"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionemssql",
            name="autenticazione_windows",
            field=models.BooleanField(
                default=False,
                help_text="Usa l'account Windows del processo (Trusted Connection). Non serve utente/password SQL.",
                verbose_name="Autenticazione Windows",
            ),
        ),
    ]
