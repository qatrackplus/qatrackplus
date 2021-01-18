
from django.db import migrations, models
from django.conf import settings


def migrate_datetimes_to_date(apps, schema_editor):

    Unit = apps.get_model('units', 'Unit')
    UnitAvailableTimeEdit = apps.get_model('units', 'UnitAvailableTimeEdit')
    UnitAvailableTime = apps.get_model('units', 'UnitAvailableTime')

    for u in Unit.objects.all():
        if u.install_date_old:
            u.install_date = u.install_date_old.date()
        u.date_acceptance = u.date_acceptance_old.date()
        u.save()

    for uate in UnitAvailableTimeEdit.objects.all():
        uate.date = uate.date_old.date()
        uate.save()

    for uat in UnitAvailableTime.objects.all():
        uat.date_changed = uat.date_changed_old.date()
        uat.save()


class Migration(migrations.Migration):
    dependencies = [
        ('units', '0015_auto_20200729_1654'),
    ]

    operations = [
        migrations.RenameField(
            model_name='unit',
            old_name='install_date',
            new_name='install_date_old',
        ),
        migrations.AddField(
            model_name='unit',
            name='install_date',
            field=models.DateField(null=True, blank=True, help_text='Optional install date'),
        ),
        migrations.RenameField(
            model_name='unit',
            old_name='date_acceptance',
            new_name='date_acceptance_old',
        ),
        migrations.AddField(
            model_name='unit',
            name='date_acceptance',
            field=models.DateField(null=True),
        ),
        migrations.RenameField(
            model_name='unitavailabletimeedit',
            old_name='date',
            new_name='date_old',
        ),
        migrations.AddField(
            model_name='unitavailabletimeedit',
            name='date',
            field=models.DateField(
                null=True
            ),
        ),
        migrations.RenameField(
            model_name='unitavailabletime',
            old_name='date_changed',
            new_name='date_changed_old',
        ),
        migrations.AddField(
            model_name='unitavailabletime',
            name='date_changed',
            field=models.DateField(
                null=True
            ),
        ),
        migrations.AlterUniqueTogether(
            name='unitavailabletime',
            unique_together=None,
        ),
        migrations.AlterUniqueTogether(
            name='unitavailabletimeedit',
            unique_together=None,
        ),

        migrations.RunPython(migrate_datetimes_to_date),

        migrations.RemoveField(
            model_name='unit',
            name='install_date_old',
        ),
        migrations.RemoveField(
            model_name='unit',
            name='date_acceptance_old',
        ),
        migrations.RemoveField(
            model_name='unitavailabletimeedit',
            name='date_old',
        ),
        migrations.RemoveField(
            model_name='unitavailabletime',
            name='date_changed_old',
        ),

        migrations.AlterField(
            model_name='unit',
            name='date_acceptance',
            field=models.DateField(
                verbose_name="Acceptance date",
                help_text='Changing acceptance date will delete unit available times that occur before it'
            ),
        ),
        migrations.AlterField(
            model_name='unitavailabletimeedit',
            name='date',
            field=models.DateField(
                help_text='Date of available time change'
            ),
        ),
        migrations.AlterField(
            model_name='unitavailabletime',
            name='date_changed',
            field=models.DateField(
                blank=True, help_text='Date the units available time changed or will change',
            )
        ),

        migrations.AlterUniqueTogether(
            name='unitavailabletime',
            unique_together=set([('unit', 'date_changed')]),
        ),
        migrations.AlterUniqueTogether(
            name='unitavailabletimeedit',
            unique_together=set([('unit', 'date')]),
        ),
    ]

    def apply(self, project_state, schema_editor, collect_sql=False):
        if settings.DATABASES['default']['ENGINE'] == "sql_server.pyodbc":
            return super().apply(project_state, schema_editor, collect_sql=collect_sql)
        else:
            return project_state
