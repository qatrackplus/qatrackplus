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

It is highly recommended that your backups do not reside on the QATrack+ server itself.
Store them on a remote system (e.g. a network or shared drive) so that if your server
loses its primary hard drive, or if the files become corrupted or locked by ransomware,
you will still have access to your backups.

.. danger::

    Ultimately, **it is up to you and your IT department to ensure your QATrack+
    installation is backed up correctly**.


Which backup method is supported
--------------------------------

**The Docker ``backup`` service is the supported database backup.** It runs
``pg_dump`` against the PostgreSQL container on a schedule, and the next section
describes it.

**Every other deployment backs up its database with its own engine's tooling**,
as part of the backup regime your IT department already runs for the rest of the
server. QATrack+ does not wrap those tools, and does not try to:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Engine
     - Use
   * - PostgreSQL
     - ``pg_dump`` - or the Docker service below, which is this
   * - MS SQL Server
     - ``BACKUP DATABASE``, SQL Server Management Studio, or your existing SQL
       Server maintenance plan
   * - MySQL / MariaDB
     - ``mysqldump``
   * - SQLite
     - a file copy taken while QATrack+ is **stopped**, or ``sqlite3 .backup``

A database backup taken with the engine's own tooling is also the only kind the
engine can promise is consistent. A file copy taken while the application is
writing is not a backup, whatever its size suggests.

The ``backup_site`` Management Command
--------------------------------------

``manage.py backup_site`` backs up the **uploaded media files** to a timestamped
directory. It does **not** back up the database on any engine.

.. important::

    **It reports, per engine, that it is not backing up the database**, and names
    the tool you should use instead. It does not attempt the database on any
    engine, so it cannot appear to have taken one.

    **The command exits zero.** There is no non-zero exit path in it, so a
    scheduled task that checks only the exit status records a success - for the
    media backup, which is all it claims. Read the output.

.. warning::

    **Check any backup set taken before 4.0.2 - on any engine.**

    Earlier versions attempted the database on SQL Server and SQLite, and both
    could mislead you:

    - **On SQL Server it reported success while writing nothing.** Measured on
      SQL Server 2022: the command printed *"Successfully backed up SQL Server
      database to ..."*, exited zero, and left the dated folders **empty**, with
      no row in ``msdb.dbo.backupset`` and *"Error: 3041 ... BACKUP failed to
      complete the command"* in the SQL Server error log at the same second. If
      you have been relying on it, **you do not have a database backup.**

    - **On SQLite it wrote the copy beside the live database**, not into your
      backup directory - on the same disk as the original, so it survived nothing
      the original did not - and took the copy while QATrack+ may have been
      writing.

    - **On MySQL, before 4.0.1**, the database was skipped silently while the
      command still reported success, so a backup set can contain media and
      settings and no database at all.

    - **On PostgreSQL it has never written a database backup.** It always said so
      rather than failing quietly, but if you were relying on it, you do not have
      one.

    In every case the remedy is the same: take a database backup now with the
    tooling in the table above, and confirm it opens.

Backups in Docker
-----------------

``deploy/docker/backup/backup.sh`` reads the database connection from the
environment rather than hard-coding it:

.. code-block:: bash

    POSTGRES_DB        # the database to dump
    POSTGRES_USER      # the role to connect as
    POSTGRES_PASSWORD  # that role's password

These are the same variables the ``postgres`` service uses, so a deployment that
sets them in its Compose environment or ``.env`` file needs no further
configuration. If they are not set the dump fails rather than silently writing a
backup of the wrong database.

.. note::

    Before 4.0.1 this script had the database name and user written into it, so a
    deployment that had changed either was dumping the wrong database, or nothing at
    all. If you have customised them, confirm your next backup contains what you
    expect.


Using Django to Dump The Database To JSON
-----------------------------------------

.. warning::
    **Do NOT use this method for your regular database backups.**
    Dumping to JSON is slow, memory-intensive, and is not a reliable backup strategy for a production database. Always use the native backup tools provided by your database engine (e.g. ``pg_dump`` for PostgreSQL, or SQL Server Management Studio for MS SQL) for your regular backups.

Restoring from Backups
----------------------

If you need to restore your QATrack+ instance from a backup (for example, when migrating to a new server or recovering from an issue), follow the general guidelines below for your deployment platform.

Linux
.....

1. **Re-install QATrack+:** Follow the standard Linux installation instructions to rebuild your server. Ensure you check out the *exact same version* of QATrack+ that you were running when the backup was taken.
2. **Restore Database:** Consult your IT department to restore the database from your automated backups using the native database tools (e.g., ``pg_restore`` or ``mysql``).
3. **Restore Settings and Media:** Copy your backed-up ``local_settings.py`` file to the ``qatrackplus/qatrack/`` directory. Extract your backed-up ``media`` folder into the ``qatrackplus/qatrack/media/`` directory.
4. **Permissions and Restart:** Ensure the web server user (e.g., ``www-data``) has the correct ownership and permissions for the restored ``media`` folder. Finally, restart the web server and your background task runner.

Windows
.......

1. **Re-install QATrack+:** Follow the standard Windows installation instructions. Ensure you check out the *exact same version* of QATrack+ that you were running when the backup was taken.
2. **Restore Database:** Consult your IT department to restore your database using SQL Server Management Studio or native MS SQL backup tools.
3. **Restore Settings and Media:** Copy your backed-up ``local_settings.py`` file to the ``qatrackplus\qatrack\`` directory. Copy your backed-up ``media`` folder into the ``qatrackplus\qatrack\media\`` directory.
4. **Permissions and Restart:** Ensure the Windows Service account or IIS application pool has write permissions to the restored ``media`` folder. Finally, restart your QATrack+ Web Service and your Django Q Scheduled Task.

Docker
......

1. **Re-deploy Containers:** On a fresh Docker host, clone the QATrack+ repository and ensure you are on the *exact same version* (branch/tag) as your backup.
2. **Restore Database:** If you are using an external database, consult your IT department to restore it. If you are using a containerized database volume, follow Docker best practices to restore the database volume from your backup archives.
3. **Restore Settings and Media:** Restore your ``local_settings.py`` file and ``media`` files to the appropriate mounted volumes or host directories as configured in your ``docker-compose.yml``.
4. **Start Containers:** Run ``docker compose up -d`` to bring the restored QATrack+ containers back online.


Appendix: if your production database is SQLite
-----------------------------------------------

SQLite is documented here as a development and small-installation option, and some
sites run it in production anyway. This appendix is for them. **It describes one
hazard that will not announce itself**, and it is a documentation note rather than a
change to the command.

.. danger::

    **``manage.py backup_site`` copies the SQLite file while QATrack+ may be writing
    to it, and the copy is usually unusable.** It calls ``shutil.copy2`` on the live
    database. It does not use SQLite's online backup, and the copy carries no
    journal, so a copy taken while a transaction is open is a torn file.

    **Measured, five runs out of five:** with one thread writing continuously, every
    ``shutil.copy2`` copy failed ``PRAGMA integrity_check``, and one could not be
    opened at all - *"database disk image is malformed"*. Over the same runs,
    ``VACUUM INTO`` produced a consistent copy every time.

    The command prints ``Copied SQLite database to ...`` and **exits zero** in both
    cases, so nothing tells you which you have. A site can hold a year of backups
    that are all unopenable and have been told nothing was wrong.

**Back up SQLite with ``VACUUM INTO``**

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
