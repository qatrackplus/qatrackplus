# Generated by Django 2.1.7 on 2019-03-14 01:10

from django.db import migrations


def stringify_null_tols(apps, schema):

    Tolerance = apps.get_model("qa", "Tolerance")
    Tolerance.objects.filter(mc_tol_choices=None).update(mc_tol_choices='')
    Tolerance.objects.filter(mc_pass_choices=None).update(mc_pass_choices='')


class Migration(migrations.Migration):

    dependencies = [
        ('qa', '0030_auto_20190129_2156'),
    ]

    operations = [migrations.RunPython(stringify_null_tols, lambda apps, sch: None)]
