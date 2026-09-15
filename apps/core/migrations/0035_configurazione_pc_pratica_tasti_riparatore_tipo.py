from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0034_configurazione_mssql_nome_database_cassa"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionepc",
            name="pratica_tasto_riparatore",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Disabilitato"),
                    ("Ctrl+S", "Ctrl+S"),
                    ("Ctrl+P", "Ctrl+P"),
                    ("Ctrl+B", "Ctrl+B"),
                    ("Ctrl+Enter", "Ctrl+Enter"),
                    ("Ctrl+Shift+S", "Ctrl+Shift+S"),
                    ("Ctrl+Shift+P", "Ctrl+Shift+P"),
                    ("Ctrl+Shift+B", "Ctrl+Shift+B"),
                    ("Esc", "Esc"),
                    ("F5", "F5"),
                    ("F6", "F6"),
                    ("F7", "F7"),
                    ("F8", "F8"),
                    ("F9", "F9"),
                    ("F10", "F10"),
                ],
                default="F6",
                help_text="Scorciatoia per portare il focus sul campo Riparatore.",
                max_length=20,
                verbose_name="Tasto Riparatore",
            ),
        ),
        migrations.AddField(
            model_name="configurazionepc",
            name="pratica_tasto_tipo_oggetto",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Disabilitato"),
                    ("Ctrl+S", "Ctrl+S"),
                    ("Ctrl+P", "Ctrl+P"),
                    ("Ctrl+B", "Ctrl+B"),
                    ("Ctrl+Enter", "Ctrl+Enter"),
                    ("Ctrl+Shift+S", "Ctrl+Shift+S"),
                    ("Ctrl+Shift+P", "Ctrl+Shift+P"),
                    ("Ctrl+Shift+B", "Ctrl+Shift+B"),
                    ("Esc", "Esc"),
                    ("F5", "F5"),
                    ("F6", "F6"),
                    ("F7", "F7"),
                    ("F8", "F8"),
                    ("F9", "F9"),
                    ("F10", "F10"),
                ],
                default="F7",
                help_text="Scorciatoia per portare il focus sul campo Tipo oggetto.",
                max_length=20,
                verbose_name="Tasto Tipo oggetto",
            ),
        ),
    ]
