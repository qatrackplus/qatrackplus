# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-11-20 21:07
from __future__ import unicode_literals

from django.db import migrations, models
import recurrence.fields


class Migration(migrations.Migration):

    dependencies = [
        ('qa', '0021_check_py3_calcs'),
    ]

    operations = [
        migrations.AddField(
            model_name='frequency',
            name='recurrences',
            field=recurrence.fields.RecurrenceField(default='', help_text='Define the recurrence rules for this frequency', verbose_name='Recurrences'),
        ),
        migrations.AlterField(
            model_name='frequency',
            name='nominal_interval',
            field=models.PositiveIntegerField(editable=False, help_text='Nominal number of days between test completions (for internal ordering purposes)'),
        ),
        migrations.AlterField(
            model_name='frequency',
            name='overdue_interval',
            field=models.PositiveIntegerField(help_text='How many days after the due date should a test with this frequency be shown as overdue'),
        ),
    ]
