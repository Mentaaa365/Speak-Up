from django.db import migrations, models


def backfill_texto_objetivo(apps, schema_editor):
    Ejercicio = apps.get_model('curriculum', 'Ejercicio')
    Ejercicio.objects.filter(texto_objetivo__isnull=True).update(texto_objetivo='')


class Migration(migrations.Migration):

    dependencies = [
        ('curriculum', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ejercicio',
            name='texto_objetivo',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.RunPython(
            backfill_texto_objetivo,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
