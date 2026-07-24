from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_configurazione_programma_layout_stile"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="liste_righe_per_pagina",
            field=models.PositiveSmallIntegerField(
                choices=[(10, "10"), (20, "20"), (50, "50"), (100, "100")],
                default=20,
                help_text=(
                    "Numero predefinito di righe nelle liste "
                    "(modificabile anche dalla barra di paginazione)."
                ),
                verbose_name="Righe per pagina nelle liste",
            ),
        ),
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="comandi_voce_attivi",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Mostra il microfono in barra e permette navigazione/paginazione a voce "
                    "(richiede Chrome/Edge e permesso microfono)."
                ),
                verbose_name="Abilita comandi vocali",
            ),
        ),
        migrations.AddField(
            model_name="configurazioneprogramma",
            name="comandi_voce_lingua",
            field=models.CharField(
                choices=[("it-IT", "Italiano"), ("en-US", "English (US)")],
                default="it-IT",
                help_text="Lingua usata dal riconoscimento vocale del browser.",
                max_length=10,
                verbose_name="Lingua riconoscimento vocale",
            ),
        ),
    ]
