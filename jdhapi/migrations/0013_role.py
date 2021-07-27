# Generated by Django 3.1.3 on 2021-05-17 14:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jdhapi', '0012_remove_article_authors'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_id', models.IntegerField()),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jdhapi.article')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jdhapi.author')),
            ],
        ),
    ]
