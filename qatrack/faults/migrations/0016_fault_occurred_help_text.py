"""Stop Fault.occurred's help_text carrying the configured date format.

It used to read `_("When did this fault occur. ") + settings.DATETIME_HELP`. A
field's help_text is part of its migration state, so deriving it from a
setting meant that any site changing the date format had a pending migration
of its own, forever - `manage.py makemigrations --check`, which the PR
checklist asks contributors to run, would fail on their install for a reason
that had nothing to do with their code.

The format hint is now added by FaultForm instead, where it belongs and where
it can follow the setting freely. No database change: help_text is metadata.

Deliberately narrow. The autodetector wanted to fold in six unrelated field
alterations that are already pending on develop for other reasons; those are
not this change's to carry.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faults', '0015_v4_0_final'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fault',
            name='occurred',
            field=models.DateTimeField(
                db_index=True,
                default=django.utils.timezone.now,
                help_text='When did this fault occur.',
                verbose_name='Date & Time fault occurred',
            ),
        ),
    ]
