# Generated by Django 2.2.3 on 2019-09-10 03:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0006_auto_20190909_2232'),
    ]

    operations = [
        migrations.AlterField(
            model_name='config',
            name='assigner',
            field=models.TextField(default='{"table":{},"progress":{}}'),
        ),
    ]