# Generated by Django 2.1.15 on 2020-05-16 01:12

from django.db import migrations

to_rename = [
    ("utc", "testlistinstance_details"),
    ("qc-summary-by-date", "testlistinstance_summary"),
    ("test_data", "testinstance_details"),
]


def change_report_types(apps, schema):

    for from_, to in to_rename:
        apps.get_model("reports", "SavedReport").objects.filter(report_type=from_).update(report_type=to)


def unchange_report_types(apps, schema):

    for to, from_ in to_rename:
        apps.get_model("reports", "SavedReport").objects.filter(report_type=from_).update(report_type=to)


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_reportschedule_last_sent'),
    ]

    operations = [
        migrations.RunPython(change_report_types, unchange_report_types)
    ]
