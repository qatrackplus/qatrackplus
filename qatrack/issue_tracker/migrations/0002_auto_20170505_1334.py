# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-05-05 17:34
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import re


class Migration(migrations.Migration):

    dependencies = [
        ('issue_tracker', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IssuePriority',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32)),
                ('colour', models.CharField(blank=True, max_length=22, null=True, validators=[django.core.validators.RegexValidator(re.compile('^rgba\\(([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]),([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]),([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5]),(0(\\.[0-9][0-9]?)?|1)\\)$', 32), 'Enter a valid color.', 'invalid')])),
                ('order', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name='issue',
            name='issue_priority',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='issue_tracker.IssuePriority'),
        ),
    ]
