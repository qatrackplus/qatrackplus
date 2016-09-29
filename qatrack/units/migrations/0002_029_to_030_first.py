# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion

def migrate_unitype_vendor_char_to_vendor(apps, schema_editor):

    UnitType = apps.get_model('units', 'UnitType')
    Vendor = apps.get_model('units', 'Vendor')

    for ut in UnitType.objects.all():

        vendor_char = ut.vendor_char
        vendor, is_new = Vendor.objects.get_or_create(name=vendor_char)
        ut.vendor = vendor
        ut.save()


class Migration(migrations.Migration):

    dependencies = [
        ('units', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Name of this site', unique=True, max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='UnitClass',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Name of this unit class', unique=True, max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Name of this vendor', unique=True, max_length=64)),
            ],
        ),
        migrations.AddField(
            model_name='unit',
            name='active',
            field=models.BooleanField(default=True, help_text='Set to false if unit is no longer in use'),
        ),
        migrations.AddField(
            model_name='unit',
            name='date_acceptance',
            field=models.DateField(help_text='Optional date of acceptance', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='type',
            field=models.ForeignKey(to='units.UnitType', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.RenameField(
            model_name='unittype',
            old_name='vendor',
            new_name='vendor_char',
        ),
        migrations.AddField(
            model_name='unittype',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='units.Vendor', null=True),
        ),
        migrations.RunPython(migrate_unitype_vendor_char_to_vendor),
        migrations.RemoveField(
            model_name='unittype',
            name='vendor_char',
        ),
        migrations.AddField(
            model_name='unit',
            name='site',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, to='units.Site'),
        ),
        migrations.AddField(
            model_name='unit',
            name='restricted',
            field=models.BooleanField(default=False, help_text='Set to false to restrict unit from operation'),
        ),
        migrations.AddField(
            model_name='unittype',
            name='unit_class',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='units.UnitClass', null=True),
        ),
    ]
