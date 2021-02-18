# Generated by Django 3.1.6 on 2021-02-18 12:26

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0003_auto_20210218_1154'),
    ]

    operations = [
        migrations.AddField(
            model_name='queue',
            name='who_timestamp',
            field=models.DateTimeField(default=datetime.datetime(2021, 2, 18, 12, 26, 38, 669709, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='queue',
            name='admins_timestamp',
            field=models.DateTimeField(default=datetime.datetime(2021, 2, 18, 12, 26, 38, 669644, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='queue',
            name='list_timestamp',
            field=models.DateTimeField(default=datetime.datetime(2021, 2, 18, 12, 26, 38, 669678, tzinfo=utc)),
        ),
    ]