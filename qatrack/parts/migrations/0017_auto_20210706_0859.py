# Generated by Django 2.2.18 on 2021-07-06 12:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parts', '0016_auto_20210127_1624'),
        ('units', '0026_room_storage'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='storage',
            unique_together=None,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='storage',
                    name='room',
                ),
            ],
            database_operations=[],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='contact',
                    name='phone_number',
                    field=models.CharField(blank=True, help_text='Contact phone number', max_length=31, verbose_name='phone number'),
                ),
            ],
            database_operations=[],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='part',
                    name='storage',
                    field=models.ManyToManyField(help_text='Storage locations for this part', related_name='parts', through='parts.PartStorageCollection', to='units.Storage', verbose_name='storage'),
                ),
            ],
            database_operations=[],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='partstoragecollection',
                    name='storage',
                    field=models.ForeignKey(help_text='Select the Storage to be associated with this Part', on_delete=django.db.models.deletion.CASCADE, to='units.Storage', verbose_name='storage'),
                )
            ],
            database_operations=[],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='partused',
                    name='from_storage',
                    field=models.ForeignKey(blank=True, help_text='Select which Storage the parts were taken from', null=True, on_delete=django.db.models.deletion.SET_NULL, to='units.Storage', verbose_name='from storage'),
                ),
            ],
            database_operations=[],
        ),
    ]