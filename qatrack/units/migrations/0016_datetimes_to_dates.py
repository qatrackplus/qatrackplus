
from django.db import migrations, models

def migrate_datetimes_to_date(apps, schema_editor):

    Unit = apps.get_model('units', 'Unit')
    UnitAvailableTimeEdit = apps.get_model('units', 'UnitAvailableTimeEdit')
    UnitAvailableTime = apps.get_model('units', 'UnitAvailableTime')

    for u in Unit.objects.all():
        if u.install_date_old:
            try:
                u.install_date = u.install_date_old.date()
            except AttributeError:
                u.install_date = u.install_date_old

        try:
            u.date_acceptance = u.date_acceptance_old.date()
        except AttributeError:
            u.date_acceptance = u.date_acceptance_old
        u.save()

    for uate in UnitAvailableTimeEdit.objects.all():
        try:
            uate.date = uate.date_old.date()
        except AttributeError:
            uate.date = uate.date_old
        uate.save()

    for uat in UnitAvailableTime.objects.all():
        try:
            uat.date_changed = uat.date_changed_old.date()
        except AttributeError:
            uat.date_changed = uat.date_changed_old
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
            field=models.DateField(null=True),
        ),
        migrations.RenameField(
            model_name='unitavailabletime',
            old_name='date_changed',
            new_name='date_changed_old',
        ),
        migrations.AddField(
            model_name='unitavailabletime',
            name='date_changed',
            field=models.DateField(null=True),
        ),

        migrations.RunPython(migrate_datetimes_to_date),

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
            field=models.DateField(help_text='Date of available time change'),
        ),
        migrations.AlterField(
            model_name='unitavailabletime',
            name='date_changed',
            field=models.DateField(blank=True, help_text='Date the units available time changed or will change', )
        ),

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
    ]

