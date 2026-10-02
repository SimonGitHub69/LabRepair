# Generated manually for Ddt.negozio (numerazione per negozio)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0045_ddt_progressivo_e_campi_busta"),
    ]

    operations = [
        migrations.AddField(
            model_name="ddt",
            name="negozio",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Negozio di emissione (numerazione DDT indipendente per sede).",
                max_length=2,
                verbose_name="Negozio",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="ddt",
            name="pratiche_ddt_numero_sezionale_attivi_uniq",
        ),
        migrations.AddConstraint(
            model_name="ddt",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("numero", "sezionale", "negozio"),
                name="pratiche_ddt_numero_sezionale_negozio_attivi_uniq",
            ),
        ),
    ]
