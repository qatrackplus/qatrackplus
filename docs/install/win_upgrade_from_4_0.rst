.. _win_upgrade_from_4_0:

Upgrading a Windows Server v4.0.0 installation to v4.0.1
========================================================

v4.0.1 is a patch release containing **no database migrations**. On Windows Server the
upgrade is a code update, a dependency sync and a restart:

1. Stop the scheduled task and the web service
2. ``git fetch`` and ``git pull``
3. ``uv sync --exact --extra win --extra mssql``
4. ``python manage.py check``
5. ``python manage.py migrate`` and ``python manage.py collectstatic``
6. Start the service and scheduled task again

You never name a version. The installation guide checks out the ``releases/4.0``
*branch* rather than a version tag, so the branch carries each patch as it is released
and a ``git pull`` is all that moves you between them.

**These steps apply to any v4.0.x patch**, not only this one. What changes between
patches is in the next section.

.. note::

    The service and scheduled task names stopped carrying version numbers in v4.0.0
    precisely so that patch upgrades would not require renaming anything. If you
    upgraded to v4.0.0 from v3.x, your service is called *QATrack+ Web Service* and your
    scheduled task *QATrack+ Django Q Cluster*.

.. include:: _upgrade_4_0_before.rst

Running the upgrade
-------------------

Stop the scheduled task and the web service:

.. code-block:: console

    >>  Stop-ScheduledTask -TaskName "QATrack+ Django Q Cluster"
    >>  Stop-Service "QATrack+ Web Service"

Fetch the new version and update the environment. You do not name a version — the
``releases/4.0`` branch you installed from carries the patch:

.. code-block:: console

    >>  cd C:\deploy\qatrackplus
    >>  git fetch origin
    >>  git pull
    >>  uv sync --exact --extra win --extra mssql

Check the installation, then run the migration step and collect static files:

.. code-block:: console

    >>  python manage.py check
    >>  python manage.py migrate
    >>  python manage.py collectstatic

Restart:

.. code-block:: console

    >>  Start-Service "QATrack+ Web Service"
    >>  Start-ScheduledTask -TaskName "QATrack+ Django Q Cluster"

.. include:: _upgrade_4_0_after.rst
