# Generated by Django 2.2.3 on 2019-08-09 19:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('player', '0003_agent_movement'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='redirected_gameid',
            field=models.TextField(default=''),
        ),
    ]