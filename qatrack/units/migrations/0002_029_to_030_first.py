# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def migrate_unitype_vendor_char_to_vendor(apps, schema_editor):

    UnitType = apps.get_model('units', 'UnitType')
    Vendor = apps.get_model('units', 'Vendor')

    for ut in UnitType.objects.all():

        vendor_char = ut.vendor_char
        vendor, is_new = Vendor.objects.get_or_create(name=vendor_char)
        ut.vendor = vendor
        ut.save()


def add_initial_available_times(apps, schema_editor):

    Unit = apps.get_model('units', 'Unit')
    UnitAvailableTime = apps.get_model('units', 'UnitAvailableTime')

    for u in Unit.objects.all():

        if not u.active:
            UnitAvailableTime.objects.create(
                date_changed=u.install_date or timezone.now(),
                unit=u,
                hours_monday=timezone.timedelta(hours=0),
                hours_tuesday=timezone.timedelta(hours=0),
                hours_wednesday=timezone.timedelta(hours=0),
                hours_thursday=timezone.timedelta(hours=0),
                hours_friday=timezone.timedelta(hours=0),
                hours_saturday=timezone.timedelta(hours=0),
                hours_sunday=timezone.timedelta(hours=0),
            )
        else:
            UnitAvailableTime.objects.create(
                date_changed=u.install_date or timezone.now(),
                unit=u,
                hours_monday=timezone.timedelta(hours=8),
                hours_tuesday=timezone.timedelta(hours=8),
                hours_wednesday=timezone.timedelta(hours=8),
                hours_thursday=timezone.timedelta(hours=8),
                hours_friday=timezone.timedelta(hours=8),
                hours_saturday=timezone.timedelta(hours=0),
                hours_sunday=timezone.timedelta(hours=0),
            )


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
                ('notes', models.TextField(blank=True, help_text='Additional notes about this vendor', max_length=255, null=True)),
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
        migrations.CreateModel(
            name='UnitAvailableTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_changed', models.DateField(help_text='Date the units available time changed or will change')),
                ('hours_monday', models.DurationField(help_text='Duration of available time on Mondays')),
                ('hours_tuesday', models.DurationField(help_text='Duration of available time on Tuesdays')),
                ('hours_wednesday', models.DurationField(help_text='Duration of available time on Wednesdays')),
                ('hours_thursday', models.DurationField(help_text='Duration of available time on Thursdays')),
                ('hours_friday', models.DurationField(help_text='Duration of available time on Fridays')),
                ('hours_saturday', models.DurationField(help_text='Duration of available time on Saturdays')),
                ('hours_sunday', models.DurationField(help_text='Duration of available time on Sundays')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='units.Unit')),
            ],
            options={'default_permissions': ('change',), 'get_latest_by': 'date_changed', 'ordering': ['-date_changed']},
        ),
        migrations.CreateModel(
            name='UnitAvailableTimeEdit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='A quick name or reason for the change', max_length=64)),
                ('date', models.DateField(help_text='Date of available time change')),
                ('hours', models.DurationField(help_text='New duration of availability')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='units.Unit')),
            ],
            options={'get_latest_by': 'date', 'ordering': ['-date']},
        ),
        migrations.AlterUniqueTogether(
            name='unitavailabletime',
            unique_together=set([('unit', 'date_changed')]),
        ),
        migrations.AlterUniqueTogether(
            name='unitavailabletimeedit',
            unique_together=set([('unit', 'date')]),
        ),
        migrations.RunPython(add_initial_available_times),
    ]
