# Generated by Django 2.2.3 on 2019-10-21 05:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customsurvey', '0002_teamevalsurveydata_difficulty'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamevalsurveydata',
            name='player_id',
            field=models.IntegerField(default=-1),
        ),
    ]
