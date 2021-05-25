# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-04 01:58
from __future__ import unicode_literals

from django.db import migrations, models

from qatrack.accounts.models import get_internal_user
from qatrack.qa.models import BOOLEAN
from qatrack.qa.utils import get_bool_tols


def create_bool_tolerances(apps, schema):

    Tolerance = apps.get_model('qa', 'Tolerance')
    User = apps.get_model('auth', 'User')

    get_internal_user(User)

    get_bool_tols(User, Tolerance)


def delete_bool_tolerances(apps, schema):
    Tolerance = apps.get_model('qa', 'Tolerance')
    Tolerance.objects.filter(type=BOOLEAN).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('qa', '0004_auto_20171103_1615'),
    ]

    operations = [
        migrations.AddField(
            model_name='tolerance',
            name='bool_warning_only',
            field=models.BooleanField(default=False, editable=False, help_text='Boolean tests not matching references should be considered at tolerance rather than action', verbose_name='Boolean Warning Only'),
        ),
        migrations.RunPython(create_bool_tolerances, delete_bool_tolerances)
    ]
