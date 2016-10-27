# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
from django.core.validators import RegexValidator
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('units', '0002_029_to_030_first'),
        ('qa', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Hours',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time', models.DurationField(help_text='The time this person spent on this service event')),
            ],
            options={'verbose_name_plural': 'Hours'},
        ),
        migrations.CreateModel(
            name='ProblemType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Enter a short name for this problem type', unique=True, max_length=64)),
                ('description', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='QAFollowup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_complete', models.BooleanField(default=False, help_text='Has this QA been completed?')),
                ('is_approved', models.BooleanField(default=False, help_text='Has the QA been approved?')),
                ('datetime_assigned', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='ServiceArea',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Enter a short name for this service area', unique=True, max_length=32)),
                ('units', models.ManyToManyField(related_name='service_areas', through='service_log.UnitServiceArea', to='units.Unit'))
            ],
        ),
        migrations.CreateModel(
            name='ServiceEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('datetime_status_changed', models.DateTimeField(null=True, blank=True)),
                ('datetime_created', models.DateTimeField()),
                ('datetime_service', models.DateTimeField(help_text='Date and time this event took place', verbose_name='Date and time')),
                ('datetime_modified', models.DateTimeField(null=True, blank=True)),
                ('srn', models.IntegerField(null=True, blank=True)),
                ('safety_precautions', models.TextField(help_text='Were any special safety precautions taken?', null=True, blank=True)),
                ('problem_description', models.TextField(help_text='Describe the problem leading to this service event')),
                ('work_description', models.TextField(help_text='Describe the work done during this service event', null=True, blank=True)),
                ('duration_service_time', models.DurationField(help_text='Enter the total time duration of this service event', null=True, verbose_name='Service time', blank=True)),
                ('duration_lost_time', models.DurationField(help_text='Enter the total clinical time lost for this service event', null=True, verbose_name='Lost time', blank=True)),
                ('problem_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='service_log.ProblemType', help_text='Select/create a problem type that describes this service event', null=True)),
                ('service_event_related', models.ManyToManyField(blank=True, help_text='Was there a previous service event that might be related to this event?', related_name='_serviceevent_service_event_related_+', to='service_log.ServiceEvent', verbose_name='Service events related')),
            ],
            options={'default_permissions': (), 'get_latest_by': 'datetime_service'},
        ),
        migrations.CreateModel(
            name='ServiceEventStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Enter a short name for this service status', unique=True, max_length=32)),
                ('is_default', models.BooleanField(default=False, help_text='Is this the default status for all service events? If set to true every other service event status will be set to false')),
                ('is_review_required', models.BooleanField(default=True, help_text='Do service events with this status require review?')),
                ('is_active', models.BooleanField(default=True, help_text='Set to false if service event status is no longer used')),
                ('description', models.TextField(help_text='Give a brief description of this service event status', max_length=64, null=True, blank=True)),
                ('colour', models.CharField(default='rgba(60,141,188,1)', max_length=22, validators=[RegexValidator(re.compile('^rgba\\(([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]),([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]),([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]),(0(\\.[0-9][0-9]?)?|1)\\)$', 32), 'Enter a valid color.', 'invalid')]))
            ],
            options={'verbose_name_plural': 'Service Event Statuses'},
        ),
        migrations.CreateModel(
            name='ServiceType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Enter a short name for this service type', unique=True, max_length=32)),
                ('is_approval_required', models.BooleanField(default=False, help_text='Does this service type require approval')),
                ('is_active', models.BooleanField(default=True, help_text='Set to false if service type is no longer used')),
            ],
        ),
        migrations.CreateModel(
            name='ThirdParty',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text="Enter this person's name", max_length=32)),
                ('vendor', models.ForeignKey(to='units.Vendor', on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={'verbose_name': 'Third Party', 'verbose_name_plural': 'Third Parties'},
        ),
        migrations.CreateModel(
            name='UnitServiceArea',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('service_area', models.ForeignKey(to='service_log.ServiceArea', on_delete=django.db.models.deletion.PROTECT)),
                ('unit', models.ForeignKey(to='units.Unit', on_delete=django.db.models.deletion.PROTECT)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={'verbose_name_plural': 'Unit Service Area Memberships'}
        ),
        migrations.CreateModel(
            name='GroupLinker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Enter this group\'s display name (ie: "Physicist reported to")', max_length=64)),
                ('description', models.TextField(blank=True, help_text='Describe the relationship between this group and service events.', null=True)),
                ('help_text', models.CharField(blank=True, help_text='Message to display when selecting user in service event form.', max_length=64, null=True)),
                ('group', models.ForeignKey(help_text='Select the group.', on_delete=django.db.models.deletion.CASCADE, to='auth.Group')),
            ],
        ),
        migrations.CreateModel(
            name='GroupLinkerInstance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime_linked', models.DateTimeField()),
                ('group_linker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='service_log.GroupLinker')),
                ('service_event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='service_log.ServiceEvent')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='serviceevent',
            name='service_status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='service_log.ServiceEventStatus', verbose_name='Status'),
        ),
        migrations.AddField(
            model_name='serviceevent',
            name='service_type',
            field=models.ForeignKey(to='service_log.ServiceType', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='serviceevent',
            name='unit_service_area',
            field=models.ForeignKey(to='service_log.UnitServiceArea', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='serviceevent',
            name='user_created_by',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='serviceevent',
            name='user_modified_by',
            field=models.ForeignKey(related_name='+', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='serviceevent',
            name='user_status_changed_by',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='serviceevent',
            name='users_reported_to',
            field=models.ManyToManyField(blank=True, help_text='Users that have been notified of this service event', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='qafollowup',
            name='service_event',
            field=models.ForeignKey(to='service_log.ServiceEvent', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='qafollowup',
            name='test_list_instance',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='qa.TestListInstance', null=True),
        ),
        migrations.AddField(
            model_name='qafollowup',
            name='unit_test_collection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='qa.UnitTestCollection', help_text='Select a TestList to perform'),
        ),
        migrations.AddField(
            model_name='qafollowup',
            name='user_assigned_by',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='hours',
            name='service_event',
            field=models.ForeignKey(to='service_log.ServiceEvent', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='hours',
            name='third_party',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='service_log.ThirdParty', null=True),
        ),
        migrations.AddField(
            model_name='hours',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='hours',
            unique_together=set([('service_event', 'third_party', 'user')]),
        ),
        migrations.AlterUniqueTogether(
            name='thirdparty',
            unique_together=set([('name', 'vendor')]),
        ),
        migrations.AlterUniqueTogether(
            name='unitservicearea',
            unique_together=set([('unit', 'service_area')]),
        ),
        migrations.AlterUniqueTogether(
            name='grouplinkerinstance',
            unique_together=set([('service_event', 'group_linker')]),
        ),
        migrations.AlterUniqueTogether(
            name='grouplinker',
            unique_together=set([('name', 'group')]),
        ),
    ]
