# Generated by Django 2.1.11 on 2019-12-03 21:08

from django.db import migrations

from qatrack.qatrack_core.utils import (
    format_as_date,
    format_datetime,
    parse_date,
    parse_datetime,
)


def datestrings_to_dates(apps, schema):

    TestInstance = apps.get_model("qa", "TestInstance")

    for ti in TestInstance.objects.filter(unit_test_info__test__type="date"):
        ti.date_value = parse_date(ti.string_value)
        ti.string_value = ""
        ti.save()

    for ti in TestInstance.objects.filter(unit_test_info__test__type="datetime"):
        ti.datetime_value = parse_datetime(ti.string_value)
        ti.string_value = ""
        ti.save()


def date_to_datestrings(apps, schema):

    TestInstance = apps.get_model("qa", "TestInstance")

    for ti in TestInstance.objects.filter(unit_test_info__test__type="date"):
        ti.string_value = format_as_date(ti.date_value)
        ti.save()

    for ti in TestInstance.objects.filter(unit_test_info__test__type="datetime"):
        ti.string_value = format_datetime(ti.datetime_value)
        ti.save()


class Migration(migrations.Migration):

    dependencies = [
        ('qa', '0045_auto_20191203_1409'),
    ]

    operations = [
        migrations.RunPython(datestrings_to_dates, date_to_datestrings),
    ]
