from django.db import migrations, models


def pratica_foto_oggetto_upload_to(instance, filename):
    return f"pratiche/{instance.uuid}/foto/{filename}"


class Migration(migrations.Migration):
    dependencies = [
        ("pratiche", "0027_pratica_cliente_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="pratica",
            name="foto_oggetto",
            field=models.FileField(
                blank=True,
                max_length=500,
                upload_to=pratica_foto_oggetto_upload_to,
                verbose_name="Foto oggetto",
            ),
        ),
    ]
