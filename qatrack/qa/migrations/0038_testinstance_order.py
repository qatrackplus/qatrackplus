# Generated by Django 2.1.11 on 2019-10-10 01:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qa', '0037_auto_20191009_1919'),
    ]

    operations = [
        migrations.AddField(
            model_name='testinstance',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
