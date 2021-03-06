# Generated by Django 2.1.15 on 2020-05-30 01:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0017_auto_20200515_2014'),
    ]

    operations = [
        migrations.AlterField(
            model_name='serviceeventnotice',
            name='notification_type',
            field=models.CharField(
                choices=[('new_se_mod_se', 'Notify when a Service Event is created or modified'),
                         ('new_se', 'Notify when a Service Event is created'),
                         ('mod_se', 'Notify when a Service Event is modified'),
                         ('stat_se', 'Notify when a Service Event Status is changed'),
                         ('rtsqa', 'Notify when Return To Service QC is changed'),
                         ('perf_rts', 'Notify when Return To Service QC is performed'),
                         ('app_rts', 'Notify when Return To Service QC is approved')],
                default='new_se_mod_se',
                max_length=128,
                verbose_name='Notification Type'
            ),
        ),
    ]
