# Generated by Django 2.2.3 on 2019-08-22 17:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0003_board_optimal_score'),
    ]

    operations = [
        migrations.AddField(
            model_name='board',
            name='waiting',
            field=models.TextField(default=''),
        ),
    ]