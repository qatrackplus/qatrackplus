# Generated by Django 2.1.11 on 2019-11-29 04:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('units', '0013_site_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='slug',
            field=models.SlugField(help_text='Unique identifier made of lowercase characters and underscores for this site', unique=True),
        ),
    ]
