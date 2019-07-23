# Generated by Django 2.2.3 on 2019-07-22 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Board',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('game_id', models.IntegerField()),
                ('width', models.IntegerField()),
                ('height', models.IntegerField()),
                ('history', models.TextField(default='[]')),
                ('score_history', models.TextField(default='[]')),
                ('pending', models.TextField(default='{}')),
                ('agents', models.TextField(default='{}')),
                ('name', models.TextField(default='')),
                ('needs_refresh', models.TextField(default='{"admin":"True"}')),
                ('locked', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timer_enabled', models.BooleanField(default=False)),
                ('main', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('available', models.BooleanField(default=True)),
                ('ongoing', models.BooleanField(default=False)),
                ('max_turns', models.IntegerField(default=0)),
                ('seq_data', models.TextField(default='{}', null=True)),
                ('AI_players', models.TextField(default='')),
                ('human_players', models.TextField(default='[]')),
                ('map_recipe', models.TextField(default='')),
                ('board_id', models.IntegerField(default=-1)),
                ('position_assignment', models.TextField(default='[]')),
                ('start_time', models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Sequence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('players', models.TextField(default='[]', null=True)),
                ('data', models.TextField(default='[]', null=True)),
            ],
        ),
    ]
