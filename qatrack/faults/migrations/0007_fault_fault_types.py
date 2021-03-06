# Generated by Django 2.2.18 on 2021-03-18 03:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faults', '0006_auto_20210317_1651'),
    ]

    operations = [
        migrations.AddField(
            model_name='fault',
            name='fault_types',
            field=models.ManyToManyField(help_text='Select the fault types that occurred', related_name='faults', to='faults.FaultType', verbose_name='fault types'),
        ),
    ]
