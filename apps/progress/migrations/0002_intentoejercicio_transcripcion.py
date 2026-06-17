from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='intentoejercicio',
            name='transcripcion',
            field=models.TextField(blank=True, null=True),
        ),
    ]
