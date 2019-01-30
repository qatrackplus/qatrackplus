# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Modality',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Descriptive name for this modality', unique=True, max_length=255, verbose_name='Name')),
            ],
            options={
                'verbose_name_plural': 'Modalities',
            },
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.PositiveIntegerField(help_text='A unique number for this unit', unique=True)),
                ('name', models.CharField(help_text='The display name for this unit', max_length=256)),
                ('serial_number', models.CharField(help_text='Optional serial number', max_length=256, null=True, blank=True)),
                ('location', models.CharField(help_text='Optional location information', max_length=256, null=True, blank=True)),
                ('install_date', models.DateField(help_text='Optional install date', null=True, blank=True)),
                ('modalities', models.ManyToManyField(to='units.Modality')),
            ],
            options={
                'ordering': ['number'],
            },
        ),
        migrations.CreateModel(
            name='UnitType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Name for this unit type', max_length=50)),
                ('vendor', models.CharField(help_text='e.g. Elekta', max_length=50)),
                ('model', models.CharField(help_text='Optional model name for this group', max_length=50, null=True, blank=True)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='unittype',
            unique_together=set([('name', 'model')]),
        ),
        migrations.AddField(
            model_name='unit',
            name='type',
            field=models.ForeignKey(to='units.UnitType', on_delete=models.PROTECT),
        ),
    ]
