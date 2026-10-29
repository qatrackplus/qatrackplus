.. _win_upgrade_from_4_0_1:

Upgrading a Windows Server 4.0.1 installation to 4.0.2
=======================================================

4.0.2 is a patch release that **does run database migrations**, unlike 4.0.1. On
Windows Server the upgrade is a backup, a code update, a dependency sync, the
migrations and a restart:

1. Stop the scheduled task and the web service
2. **Back up the database, and confirm the backup file is readable**
3. ``git fetch`` and ``git pull``
4. ``uv sync --exact --extra win --extra mssql``, then activate ``.venv``
5. ``python manage.py check --database default``
6. ``python manage.py migrate`` and ``python manage.py collectstatic``
7. Start the service and scheduled task again

You never name a version. The installation guide checks out the ``releases/4.0``
*branch* rather than a version tag, so the branch carries each patch as it is released
and a ``git pull`` is all that moves you between them.

**These steps apply to any 4.0.x patch**, not only this one. What changes between
patches is in the next section.

.. important::

    Of the three supported deployments - Ubuntu Linux, Windows Server and Docker -
    Windows is the one where this release changes the database most: it is the SQL
    Server deployment, and the unique constraints the 4.0 upgrade dropped are restored
    here. Read the SQL Server note below before you start.

.. include:: _upgrade_4_0_1_before.rst

Running the upgrade
-------------------

Stop the scheduled task and the web service:

.. code-block:: console

    >>  Stop-ScheduledTask -TaskName "QATrack+ Django Q Cluster"
    >>  Stop-Service "QATrack+ Web Service"

Back up the database with the service stopped, and check the backup before going
further — see :ref:`qatrack_backup`. In SQL Server Management Studio, take a full
backup and then run a ``RESTORE VERIFYONLY`` against the file it produced:

.. code-block:: sql

    BACKUP DATABASE qatrackplus TO DISK = 'C:\backups\qatrackplus-pre-4.0.2.bak' WITH INIT;
    RESTORE VERIFYONLY FROM DISK = 'C:\backups\qatrackplus-pre-4.0.2.bak';

**Choose that folder by what SQL Server can write to, not by what you can.** The file
is written by the SQL Server service account rather than by you, so a folder you can
save into may still be refused. The instance's own default backup folder is always
writable, and this prints it:

.. code-block:: sql

    SELECT SERVERPROPERTY('InstanceDefaultBackupPath');

Then copy the file off the server. A backup beside the database it came from is one
disk failure away from being no backup at all.

.. dropdown:: If SQL Server Management Studio is not installed
    :color: warning
    :icon: terminal

    SSMS is a prerequisite for *installing* QATrack+, but it may never have been
    installed on a server somebody else set up, and it is not needed here. The same
    two statements run through ``sqlcmd``, which comes with the SQL Server command
    line tools:

    .. code-block:: console

        >>  sqlcmd -S .\SQLEXPRESS -E -C -Q "BACKUP DATABASE qatrackplus TO DISK = 'C:\backups\qatrackplus-pre-4.0.2.bak' WITH INIT;"
        >>  sqlcmd -S .\SQLEXPRESS -E -C -Q "RESTORE VERIFYONLY FROM DISK = 'C:\backups\qatrackplus-pre-4.0.2.bak';"

    ``-E`` signs in as your Windows account, and ``-C`` trusts the certificate the
    instance presents: current ``sqlcmd`` builds on ODBC Driver 18, which encrypts by
    default and **refuses a local instance's self-signed certificate without it**,
    with *"The certificate chain was issued by an authority that is not trusted"*.
    Replace ``.\SQLEXPRESS`` with your own instance name.

.. note::

    ``RESTORE VERIFYONLY`` proves the file is complete and readable. **It does not
    prove the database restores from it.** The only thing that proves that is a
    restore, and :ref:`backup_verify_restore` is the three-statement version that
    leaves your live database alone. Worth doing once, on a site whose backups have
    never been restored.

Back up the uploaded files too. **They are not in the database**, and a backup
without them is not a complete set:

.. code-block:: console

    >>  Compress-Archive -Path C:\deploy\qatrackplus\qatrack\media -DestinationPath C:\backups\qatrackplus-media-pre-4.0.2.zip

``python manage.py backup_site`` archives the same folder if you would rather use it -
on every engine, including this one, even though it declines the database itself.

Fetch the new version and update the environment. You do not name a version — the
``releases/4.0`` branch you installed from carries the patch:

.. code-block:: console

    >>  cd C:\deploy\qatrackplus
    >>  git fetch origin
    >>  git pull
    >>  uv sync --exact --extra win --extra mssql

Activate the environment. ``uv sync`` updates ``.venv`` but does not activate it,
and the commands below are run with the environment's own ``python``:

.. code-block:: console

    >>  .\.venv\Scripts\Activate.ps1

Your command prompt should now be prefixed with ``(qatrackplus)`` or ``(.venv)``.
Without this, in a fresh PowerShell window ``python`` is the system interpreter -
or Windows' Python Store alias, which opens the Microsoft Store instead of running
anything - so the commands below would either fail on missing dependencies or
run against the wrong environment, while your services are stopped.

Check the installation. **The** ``--database`` **is deliberate:** the missing-constraint
warnings have to ask SQL Server what it enforces, so they only appear when a connection
is in play. Plain ``manage.py check`` reports no issues on a database that is missing
all sixteen. The ``migrate`` that follows is what repairs them — the warnings are not
asking you to act:

.. code-block:: console

    >>  python manage.py check --database default
    >>  python manage.py check_unique_constraints

Then run the migrations and collect the static files:

.. code-block:: console

    >>  python manage.py migrate
    >>  python manage.py collectstatic --noinput

Restart:

.. code-block:: console

    >>  Start-Service "QATrack+ Web Service"
    >>  Start-ScheduledTask -TaskName "QATrack+ Django Q Cluster"

.. include:: _upgrade_4_0_1_after.rst
