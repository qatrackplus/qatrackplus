# Generated by Django 2.1.15 on 2021-01-27 21:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parts', '0015_merge_20201231_0928'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='phone_number',
            field=models.CharField(blank=True, help_text='Company phone number', max_length=31, verbose_name='phone number'),
        ),
    ]
