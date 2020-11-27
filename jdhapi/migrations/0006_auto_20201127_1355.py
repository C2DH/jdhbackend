# Generated by Django 3.1.3 on 2020-11-27 12:55

from django.db import migrations, models
import jdhapi.models


class Migration(migrations.Migration):

    dependencies = [
        ('jdhapi', '0005_auto_20201123_1349'),
    ]

    operations = [
        migrations.AddField(
            model_name='abstract',
            name='comment',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='abstract',
            name='pid',
            field=models.CharField(db_index=True, default=jdhapi.models.create_short_url, max_length=255),
        ),
    ]
