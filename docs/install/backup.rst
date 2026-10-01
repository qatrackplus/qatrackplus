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


The ``backup_site`` Management Command
--------------------------------------

``manage.py backup_site`` writes the database and the uploaded media files to a
timestamped directory.

.. warning::

    **It can only back up the database on PostgreSQL and SQLite.** On MySQL, or any
    other engine, it reports that it cannot and that step fails. Earlier versions
    skipped the database silently and still reported success, so check that the
    database file is actually present in any backup set produced before 4.0.1. For
    MySQL, use ``mysqldump``.

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
