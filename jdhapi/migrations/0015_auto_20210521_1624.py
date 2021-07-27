# Generated by Django 3.1.3 on 2021-05-21 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jdhapi', '0014_article_authors'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abstract',
            name='status',
            field=models.CharField(choices=[('SUBMITTED', 'Submitted'), ('ACCEPTED', 'Accepted'), ('DECLINED', 'Declined'), ('ABANDONMENT', 'Abandonment')], default='SUBMITTED', max_length=15),
        ),
    ]
