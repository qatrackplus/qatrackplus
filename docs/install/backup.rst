.. _qatrack_backup:

Backing up QATrack+
===================

It is **highly** recommended you put an automated backup solution in place for
your QATrack+ installation. We expect users to consult with their internal IT
departments for guidance on implementing a robust, automated backup strategy.

At a minimum, you must ensure that you keep secure, off-server backups of:

1. Your database (e.g., SQL Server, PostgreSQL, MySQL)
2. Your ``local_settings.py`` file (located in ``qatrackplus\qatrack\local_settings.py`` or ``qatrackplus/qatrack/local_settings.py``)
3. Your ``media`` folder (located in ``qatrackplus\qatrack\media`` or ``qatrackplus/qatrack/media``)

On a Docker site, your settings are in ``deploy/docker/.env`` rather than
``local_settings.py``; see `Backups in Docker`_ below.

It is highly recommended that your backups do not reside on the QATrack+ server itself.
Store them on a remote system (e.g. a network or shared drive) so that if your server
loses its primary hard drive, or if the files become corrupted or locked by ransomware,
you will still have access to your backups.

.. danger::

    Ultimately, **it is up to you and your IT department to ensure your QATrack+
    installation is backed up correctly**.

.. note::

    **Not sure your backups are sound? Please ask - we would love to help with
    this.**

    Getting a site to where it can be restored on demand is one of the most
    valuable things you can do for it, and helping with that is work we genuinely
    enjoy: looking at what you already have, finding what is missing, getting a
    readable backup out of the database you are actually running, and sequencing an
    upgrade around it. Plenty of sites start from exactly there, usually for
    reasons that have nothing to do with the people running them now.

    Bring whatever you have to the :mailinglist:`mailing list <>`. Before an
    upgrade is ideal, because there is time to do it unhurried and in the right
    order - but any time is welcome, and no starting point is too untidy to bring
    us. We would be delighted to hear from you.


The ``backup_site`` Management Command
--------------------------------------

``manage.py backup_site`` writes the database and the uploaded media files to a
timestamped directory.

.. warning::

    **Your uploaded files are archived on every engine**, so it is a complete
    answer for the half of a backup set that is not in the database.

    **The database is another matter: it backs that up only on SQLite.** On
    PostgreSQL, MySQL and SQL Server it says so and names the tool to use instead -
    ``pg_dump``, ``mysqldump``, or SQL Server's own ``BACKUP DATABASE``.

    **Check where it wrote.** The directory comes from ``BACKUP_DIR``, which the
    shipped settings set to a Windows path, ``C:\deploy\backups``. On a Linux
    server that has not overridden it, the command creates a folder of that literal
    name inside your QATrack+ directory and reports success. Set ``BACKUP_DIR`` in
    ``local_settings.py`` before relying on the command, and read the path it prints.

    **The command exits zero either way.** There is no non-zero exit path in it, so
    a scheduled task that checks only the exit status records a success whatever
    happened. Read the output, or check what is in the dated directory.

    **If you have been relying on this command for your database, check what your
    backup sets actually contain.** Before 4.0.2 it wrote nothing for the database
    on PostgreSQL or MySQL and said so; on SQL Server it could print *Successfully
    backed up* while writing nothing at all, which is why it no longer attempts
    that engine; and on SQLite it wrote the copy beside the live database instead
    of into the backup directory, where nothing pruned it and a disk failure took
    both. A set from an earlier release may be missing the database, the uploads,
    or both.

.. _backup_verify_restore:

Proving a backup restores, and not only that it reads
-----------------------------------------------------

The cheap checks - ``pg_restore --file=/dev/null``, ``RESTORE VERIFYONLY``, a
``-- Dump completed`` line at the end of a ``mysqldump`` - tell you the file is
complete and readable. **They do not tell you a database comes back out of it.**
Only a restore does that, and it does not have to go anywhere near your live
database: restore into a scratch name, count something, drop it.

**SQL Server.** The data file paths inside the backup are what collide, so they are
moved; ``FILELISTONLY`` prints the logical names to move:

.. code-block:: sql

    RESTORE FILELISTONLY FROM DISK = 'C:\backups\qatrackplus-pre-4.0.2.bak';

    RESTORE DATABASE qatrackplus_restoretest
        FROM DISK = 'C:\backups\qatrackplus-pre-4.0.2.bak'
        WITH MOVE 'qatrackplus' TO 'C:\backups\restoretest.mdf',
             MOVE 'qatrackplus_log' TO 'C:\backups\restoretest_log.ldf';

    SELECT COUNT(*) FROM qatrackplus_restoretest.dbo.qa_testlistinstance;
    DROP DATABASE qatrackplus_restoretest;

**PostgreSQL:**

.. code-block:: bash

    createdb -U postgres qatrackplus_restoretest
    pg_restore -U postgres -d qatrackplus_restoretest ~/qatrackplus-pre-4.0.2.dump
    psql -U postgres -d qatrackplus_restoretest -c 'select count(*) from qa_testlistinstance'
    dropdb -U postgres qatrackplus_restoretest

**MySQL:**

.. code-block:: bash

    mysql -u root -p -e 'create database qatrackplus_restoretest'
    mysql -u root -p qatrackplus_restoretest < ~/qatrackplus-pre-4.0.2.sql
    mysql -u root -p -e 'select count(*) from qatrackplus_restoretest.qa_testlistinstance'
    mysql -u root -p -e 'drop database qatrackplus_restoretest'

Compare the count with the same count on your live site - *Unreviewed* on the QC
review page is a quick substitute if you would rather not run SQL twice.

.. note::

    **What a scratch restore on the same server cannot tell you**, and it is the
    thing a real recovery runs into first: the database users and their permissions
    already exist there. Restoring onto a *new* server, where they do not, is where
    restores actually fail - a PostgreSQL dump reports its missing roles and carries
    on, or rolls the whole restore back under ``--single-transaction``; a MySQL dump
    carries no permissions at all and restores into a database nothing can connect
    to; and a restored SQL Server database brings orphaned users whose logins have to
    be re-mapped.

    That is why the first step under *Restoring from Backups* below is to create
    those accounts, on every platform. If you ever rehearse a full recovery, rehearse
    it somewhere that has never held this site.

Backups in Docker
-----------------

The Docker deployment's ``backup`` service backs up the database and uploaded
files every night, and comes with ``restore-db`` and ``restore-media`` commands to
put a backup back. :ref:`docker_backups` in the Docker guide explains how to use
them and how to keep copies off the server. Its backups can only be read by root
on the server, so copy them off it with ``sudo``.

A backup does not include your settings file, ``deploy/docker/.env``, or your
HTTPS certificates in ``deploy/docker/user-data/ssl``, so keep copies of those
yourself.

The ``backup`` service connects to the database with ``POSTGRES_DB``,
``POSTGRES_USER`` and ``POSTGRES_PASSWORD`` from ``deploy/docker/.env``, the same
settings the ``postgres`` service uses, so it needs no setup of its own. If one of
them is missing from ``.env``, the backup stops with an *unbound variable* error
before it runs ``pg_dump``, rather than backing up the wrong database.

.. note::

    Before 4.0.1 the backup script had the database name and user written into it, so a
    deployment that had changed either was dumping the wrong database, or nothing at
    all. If you have customised them, confirm your next backup contains what you
    expect.


Using Django to Dump The Database To JSON
-----------------------------------------

.. warning::
    **Do NOT use this method for your regular database backups.**
    Dumping to JSON is slow, memory-intensive, and is not a reliable backup strategy for a production database. Always use the native backup tools provided by your database engine (e.g. ``pg_dump`` for PostgreSQL, or SQL Server Management Studio for MS SQL) for your regular backups.

It is, however, the only backup format that does not care which database engine you
are running, so it is the right tool for two jobs: **moving a site between engines**
(SQL Server to PostgreSQL, say) and **seeding a test or demonstration instance** from
a known state.

**What has actually been tested, and what has not.** The commands below have been
tested end to end in two configurations:

.. list-table::
    :header-rows: 1
    :widths: 40 60

    * - Tested
      - Not tested
    * - QATrack+ 4.0.1 → 4.0.1, and 4.0.2 → 4.0.2
      - any version change, e.g. 4.0.1 → 4.0.2
    * - PostgreSQL 16.15 → PostgreSQL 16.15
      - SQL Server or MySQL at either end
    * - **PostgreSQL 16 → SQLite**
      - SQLite or PostgreSQL → SQL Server or MySQL
    * - Ubuntu 24.04 → the same server
      - a different server, or Linux ↔ Windows
    * - 3,460 objects, and 1,179 objects
      - a site of clinical size

A site of 3,460 objects was dumped, its database dropped, and the site rebuilt from
the dump alone; every object count matched the original. Separately, a 1,179-object
site on PostgreSQL 16 was dumped and loaded into an empty SQLite database -
``migrate``, ``createcachetable``, ``loaddata``, in that order - and every row count
matched the source, with all 1,179 objects installed.

.. warning::

    **One engine change has been rehearsed; the ones most sites need have not.**
    PostgreSQL → SQLite worked exactly as described above. **SQL Server and MySQL have
    not been exercised at either end**, which leaves out the move most often asked
    about - SQL Server to PostgreSQL - and anything involving MySQL. Those remain
    something to rehearse on a copy first, verify by restoring, and compare object
    counts against the source, rather than a procedure known to work.

    A cross-engine move is also where the primary keys matter: read the note below
    about ``--natural-foreign`` and ``--natural-primary`` before you dump, because on
    4.0.x they produce a file this version cannot load back.

    The same applies to a version change. ``loaddata`` writes rows directly, so a dump
    taken on one QATrack+ version carries that version's schema expectations; restore
    it onto the same version unless you have tested otherwise.

**Exporting**

.. code-block:: bash

    python manage.py dumpdata --indent 1 \
        -e contenttypes -e auth.permission -e sessions -e admin.logentry -e django_q \
        > qatrack-export.json

The exclusions matter. ``contenttypes`` and ``auth.permission`` are rebuilt by
``migrate`` and clash on import if they are in the file; ``sessions``,
``admin.logentry`` and ``django_q`` are transient and only make the file larger.

.. danger::

    **On 4.0.x, do not add the natural-key options** (``--natural-foreign``,
    ``--natural-primary``). They produce
    a file that QATrack+ **cannot load back**. Three models - test list sublists, service
    areas and service types - define a natural key without the matching lookup the
    deserializer then needs, so a foreign key is written as a list and the import stops
    with::

        DeserializationError: Problem installing fixture ...
        ["“['Accelerator']” value must be an integer."]: (service_log.unitservicearea:pk=1)

    This was measured, not inferred - the restore failed at that line and left an empty
    database. Note where that leaves you: ``loaddata`` empties the tables it is loading
    into before it reaches the row it cannot resolve, so the attempt does not fail
    harmlessly. The plain integer-primary-key form above restores correctly.

    **This restriction is specific to the 4.0.x series.** The three missing lookups are
    fixed from 4.1 onwards, where the same export restores correctly. An export taken on
    4.1 with natural keys will still not load into a 4.0.x installation, which does not
    have those lookups.

**Restoring**

.. code-block:: bash

    # 1. an empty database, owned by your QATrack+ database user
    # 2. then:
    python manage.py migrate
    python manage.py createcachetable
    python manage.py loaddata qatrack-export.json

``createcachetable`` must come **before** ``loaddata``, for the same reason it does
during a fresh install: loading records fires cache-invalidation signals, and they
need the cache table to exist.

Do **not** run ``loaddata fixtures/defaults/*/*`` first. The export already contains
those rows, and loading them twice gives you duplicate categories, statuses and unit
types.

.. note::

    Verify a dump by restoring it, not by looking at it. A JSON file that was written
    without error can still be one your site cannot read back - which on 4.0.x is exactly
    what ``--natural-foreign`` produces.

Restoring from Backups
----------------------

If you need to restore your QATrack+ instance from a backup (for example, when migrating to a new server or recovering from an issue), follow the general guidelines below for your deployment platform.

Restore onto the same version of QATrack+ that made the backup, then upgrade as usual if you need to. Never restore a backup into an older version of QATrack+ than the one that made it. The Docker deployment's ``restore-db`` can also restore backups made by its 4.0.0 and 4.0.1 releases directly into the current release (see :ref:`docker_backups`).

Linux
.....

1. **Re-install QATrack+:** Follow the standard Linux installation instructions to rebuild your server. Check out the same version of QATrack+ that you were running when the backup was taken.
2. **Create the database users first.** A dump records the permissions it granted, and your new server has none of the accounts those grants name, so create them - with the same names - before restoring anything. The installation instructions create the one QATrack+ connects as; if you also made a read-only user for :ref:`SQL Reports <qatrack-config>`, create that one too. **Measured on PostgreSQL 16, restoring a dump from a site with a read-only reports user onto a server that did not have it:** ``pg_restore`` reported the missing role 120 times and restored the data anyway, leaving a database whose permissions are wrong; and with ``--single-transaction``, which is what the Docker ``restore-db`` script uses, the whole restore was rolled back and no tables existed afterwards.
3. **Restore Database:** Consult your IT department to restore the database from your automated backups using the native database tools (e.g., ``pg_restore`` or ``mysql``).
4. **Restore Settings and Media:** Copy your backed-up ``local_settings.py`` file to the ``qatrackplus/qatrack/`` directory. Extract your backed-up ``media`` folder into the ``qatrackplus/qatrack/media/`` directory.
5. **Permissions and Restart:** Ensure the web server user (e.g., ``www-data``) has the correct ownership and permissions for the restored ``media`` folder. Finally, restart the web server and your background task runner.

Windows
.......

1. **Re-install QATrack+:** Follow the standard Windows installation instructions. Check out the same version of QATrack+ that you were running when the backup was taken.
2. **Reconnect the restored users to this instance's logins.** Restoring a SQL Server database brings its *users* with it, but a user is tied to a login by an internal ID, and a login you create on the new instance gets a new one - so the restored users are orphaned **even if you create the logins first**. Create the logins QATrack+ uses (``CREATE LOGIN``), restore, and then map each restored user to its login: ``ALTER USER <user> WITH LOGIN = <login>``. That last step is the one that matters. Measured on SQL Server 2025: without it, QATrack+ fails with ``Login failed for user 'qatrack'. (18456)`` and ``Cannot open database ... The login failed. (4060)`` - and with the logins created but unmapped, it takes about 80 seconds to fail while the driver retries. After the mapping, both connections work and the row counts match the source exactly.
3. **Restore Database:** Consult your IT department to restore your database using SQL Server Management Studio or native MS SQL backup tools.
4. **Restore Settings and Media:** Copy your backed-up ``local_settings.py`` file to the ``qatrackplus\qatrack\`` directory. Copy your backed-up ``media`` folder into the ``qatrackplus\qatrack\media\`` directory.
5. **Permissions and Restart:** Ensure the Windows Service account or IIS application pool has write permissions to the restored ``media`` folder. Finally, restart your QATrack+ Web Service and your Django Q Scheduled Task.

Docker
......

1. **Set QATrack+ up again:** On a Linux server, follow :ref:`docker_setup`, checking out the same version of QATrack+ that made the backup. When you reach the settings file, copy your backed-up ``.env`` into ``deploy/docker`` instead of making a new one, and put ``user-data/ssl`` back too if you use HTTPS. Put ``user-data/ldap`` back if you use LDAPS with your organization's own CA, and, if you added your own Python packages, put your copy of ``deploy/docker/site-requirements`` (``requirements.txt`` and any wheel files) back before you run ``docker compose build``. Backups contain none of these, and git does not keep ``site-requirements``, so keep copies of them yourself.
2. **Restore the database and uploaded files:** Follow the restore steps in :ref:`docker_backups`, which use ``restore-db`` and ``docker compose run --rm restore-media``.


Appendix: if your production database is SQLite
-----------------------------------------------

SQLite is documented here as a development and small-installation option, and some
sites run it in production anyway. This appendix is for them.

.. warning::

    **Backup sets this site took before 4.0.2 may hold SQLite copies that will not
    open.** Until 4.0.2 ``manage.py backup_site`` copied the database file with
    ``shutil.copy2`` while QATrack+ could be writing to it, and wrote the copy
    *beside the live database* rather than into the backup directory, where nothing
    pruned it and a disk failure took both.

    **Measured, five runs out of five:** with one thread writing continuously, every
    ``shutil.copy2`` copy failed ``PRAGMA integrity_check``, and one could not be
    opened at all - *"database disk image is malformed"*.

    **4.0.2 takes the copy through SQLite's own online backup**, which is safe while
    the site is in use, and writes it into the dated backup directory with the rest of
    the set. Copies taken by 4.0.2 and later are consistent; older ones need checking,
    and the check is at the end of this appendix.

    **The command still exits zero whatever happens**, here as everywhere else, so
    read its output rather than its exit status.

If you would rather take SQLite backups outside QATrack+ - from ``cron``, or as part
of a wider backup job - the rest of this appendix is how, and the verification step
applies to any copy however it was made.

**Back up SQLite with** ``VACUUM INTO``

``VACUUM INTO`` is SQLite's own online backup. It takes a read lock, so it is safe
while the site is in use, and it writes a compacted, consistent database:

.. code-block:: shell

    DB=/path/to/your/qatrack.db
    OUT=/path/to/backups/qatrack-$(date +%Y-%m-%d).db
    sqlite3 "$DB" "VACUUM INTO '$OUT'"

If ``sqlite3`` is not installed, Python's bundled module does the same thing:

.. code-block:: shell

    python -c "import sqlite3,sys; con=sqlite3.connect(sys.argv[1]); \
    con.execute('vacuum into ?', (sys.argv[2],)); con.close()" "$DB" "$OUT"

**Always verify the copy.** This is the step that distinguishes a backup from a file:

.. code-block:: shell

    sqlite3 "$OUT" "PRAGMA integrity_check;"      # must print: ok
    sqlite3 "$OUT" "SELECT COUNT(*) FROM qa_testinstance;"

A backup that prints anything other than ``ok`` is not a backup. Check it when you
make it, not when you need it.

**What to do with the shipped command**

``backup_site`` still backs up the uploaded media files usefully, so it is not
useless on SQLite - **treat its database step as not having happened.** Run
``VACUUM INTO`` alongside it, keep both outputs together, and verify the database
copy.

**Two further things worth knowing before you rely on SQLite in production**

- **One writer at a time.** SQLite serialises writes across the whole database, so a
  long write blocks every other write. QATrack+ runs a scheduled task process as well
  as the web process, so those two compete.
- **Upgrades work, and have been tested.** A populated v3.1.1.4 SQLite database
  migrates to 4.0 cleanly - 39 migrations, no errors, no rows lost - so this
  appendix is about your backups and not about your ability to upgrade.

  One caveat that affects nobody upgrading in place, but will catch anyone
  *installing* an old QATrack+ today to rehearse an upgrade: **Django 2.2, which
  v3.1.1.4 pins, cannot replay those migrations against a SQLite newer than 3.26.**
  The rebuild leaves foreign keys pointing at a dropped ``..._old`` table, and the
  error reads like data corruption. Rehearse on PostgreSQL, or on a SQLite of the
  period.
