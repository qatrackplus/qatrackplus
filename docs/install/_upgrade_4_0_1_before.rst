.. This file is a fragment, pulled into each platform's 4.0.1 to 4.0.2 upgrade guide
   with `.. include::`. It is excluded from the build in conf.py, because an included
   file that is also read as a document has every label in it reported as a
   duplicate.

   It holds what is true of the release regardless of how QATrack+ is deployed, so
   the per-platform guides differ only where the commands differ.

Before you start
----------------

**Back up your database and your uploads, and check the backup opens.** That is
the same thing you would do before any QATrack+ upgrade.

**If you have edited any files inside** ``qatrack/``, read *Upgrading an
installation you have modified* at the end of this page **before you pull**: it
asks you to record what you changed while that is still a one-line command.

.. note::

    4.0.2 runs migrations, the way most QATrack+ releases have; 4.0.1 was the
    unusual one in having none. Nothing here deletes data: the migrations record
    field descriptions the models have declared for several releases, and restore
    unique constraints that SQL Server lost during the 4.0 upgrade.

    :ref:`qatrack_backup` says what a backup set has to contain, and - if your
    production database is SQLite - how to take one that is actually readable,
    which a file copy of a live database is not.

**What you will see.** ``migrate`` prints one line per migration. Upgrading 4.0.1
to 4.0.2 applies **eight**, one for most applications plus one that creates the
cache table:

.. code-block:: text

    Applying attachments.0011_v4_0_2_final... OK
    Applying faults.0016_v4_0_2_final... OK
    Applying parts.0019_v4_0_2_final... OK
    Applying qa.0061_v4_0_2_final... OK
    Applying qatrack_core.0002_cache_table... OK
    Applying reports.0011_v4_0_2_final... OK
    Applying service_log.0029_v4_0_2_final... OK
    Applying units.0022_v4_0_2_final... OK

``migrate`` applies them in dependency order rather than the alphabetical order
listed above - ``parts`` first, ``service_log`` last on most sites - so the eight
lines appear in a different sequence to the one here. It also prints a handful of
lines that are not migrations at all: *"... next run updated to ..."* for each
scheduled task it already had, and one *"qatrack.reports.tasks.run_reports schedule
created"*. Those are django-q2 re-reading its schedule, not something the upgrade
switched on.

Between them the eight carry **194 field alterations**, two model-options changes and
six data steps. The field alterations are the bulk of it and are the least
interesting part: they bring the recorded schema into line with what the models
have declared for several releases, so most make no change to your tables at all.
The ``qa`` one is the largest at 132.

Three of those lines are worth recognising:

- **The SQL Server unique-constraint repair runs in four of them** -
  ``parts.0019``, ``qa.0061``, ``service_log.0029`` and ``units.0022``. Each
  restores the unique indexes that engine lost for its own application's tables,
  so on SQL Server these are the four lines that matter. ``qa.0061`` is the slowest,
  carrying 132 of the 194 field alterations as well as its share of the repair. Of
  the remaining four, three are field state only; ``qatrack_core.0002_cache_table``
  is the exception and is described next.
- **The cache table migration**, ``qatrack_core.0002_cache_table``, creates the
  cache table. Until 4.0.2 that table was created by ``manage.py createcachetable``
  and by nothing else, so a database that had been migrated but never had that
  command run would fail at runtime. This migration removes that gap; if you have
  already run ``createcachetable``, it finds the table and does nothing.
- **The permission rename**, ``service_log.0029_v4_0_2_final``, corrects one label.
  In 4.0.x both "can view service event" and "can review service event" were
  labelled *Can review service event*, so the admin's permission list showed the
  same words twice for two different rights and there was no way to tell them apart
  when assigning them. The view permission now reads **Can view service event**.

  This is the one change in the upgrade an administrator will *see*. If you had
  already corrected the wording yourself, the migration leaves your version
  alone - it only replaces the exact 4.0.x text.

  **Check your groups after upgrading** if you assigned either permission by
  picking it from that list, because until now the two were indistinguishable
  there. ``review_serviceevent`` is the one that also allows changing a service
  event's status.

If ``migrate`` applies more than these eight, the most likely reason is simply
that the site was on 4.0.0 rather than 4.0.1, so it is catching up on 4.0.1's
migrations too - see :ref:`the 4.0.0 upgrade guide <linux_upgrade_from_4_0>` for
what those are. Worth a look either way, since it tells you where the database
actually started.

.. note::

    These eight are the whole 4.0.1 to 4.0.2 step. A **fresh** installation runs
    the full history instead - several hundred migrations, and several minutes -
    which is normal, and not what an upgrading site sees.

.. dropdown:: If you are on SQL Server, read this one
    :color: warning
    :icon: alert

    The 4.0 migrations silently dropped unique indexes on SQL Server -
    ``mssql-django`` drops them when an unrelated field change retypes a primary
    key, and never puts them back. **Your database has been accepting duplicate
    rows that other backends would reject**, including on
    ``TestListInstance.user_key``, whose job is to keep API submissions unique.

    **4.0.2 restores them.** You do not have to do anything, but two things are
    worth knowing:

    - ``migrate`` **prints a warning for each missing constraint**
      (``qatrack.W014``) before it applies anything, and then the same ``migrate``
      repairs them. The warnings are not telling you to act.

      To see them without migrating, the command is ``python manage.py check
      --database default``. **Plain** ``manage.py check`` **will not show them**: this
      check has to ask the database what it enforces, so it is registered to run only
      when a connection is in play, and ``check`` without ``--database`` reports
      "System check identified no issues" on a database that is missing all sixteen.
    - **Rows that already violate a constraint block its repair.** Run
      ``manage.py check_unique_constraints`` first to see whether you have any. A
      constraint that cannot be created is reported and skipped; the upgrade still
      finishes.

.. dropdown:: Dates and times will look different, and that is this release
    :color: info
    :icon: info

    **Dates now display as** ``YYYY-MM-DD`` **by default**, in every language, and the
    date pickers write back the same format they show.

    This is the fix for a released bug: 4.0 wrote a date into a form in one format
    and read it back in another, so a pre-filled date was silently replaced with an
    unrelated one - usually months away and at midnight - before anyone had touched
    the page.

    If your site needs its previous appearance, set ``QATRACK_DATE_FORMAT`` and
    ``QATRACK_DATETIME_FORMAT`` in ``local_settings.py``. The release notes give the
    values that reproduce 4.0's display.
