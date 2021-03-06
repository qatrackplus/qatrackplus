# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-03-03 02:41
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('qa', '0010_auto_20171208_1411'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnitTestInfoChange',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference_changed', models.BooleanField()),
                ('tolerance_changed', models.BooleanField()),
                ('comment', models.TextField(help_text='Reason for the change')),
                ('changed', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('reference', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='qa.Reference', verbose_name='Old Reference')),
                ('tolerance', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='qa.Tolerance', verbose_name='Old Tolerance')),
                ('unit_test_info', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='qa.UnitTestInfo')),
            ],
        ),
    ]
