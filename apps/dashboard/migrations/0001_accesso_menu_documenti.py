from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AccessoMenu",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            options={
                "verbose_name": "Accesso menu",
                "verbose_name_plural": "Accessi menu",
                "permissions": [
                    ("access_documenti", "Può accedere al menu Documenti"),
                ],
                "default_permissions": (),
            },
        ),
    ]
