.. _linux_upgrade_from_4_0:

Upgrading an Ubuntu Linux 4.0.0 installation to 4.0.1
=======================================================

4.0.1 is a patch release containing **no database migrations**. On Ubuntu Linux the
upgrade is a code update, a dependency sync and a restart:

1. Stop the background services
2. ``git fetch`` and ``git pull``
3. ``uv sync`` with your database's extra
4. ``python manage.py check``
5. ``python manage.py migrate`` and ``python manage.py collectstatic``
6. Fix the ownership of the ``logs`` and ``qatrack/media`` folders (once)
7. Start the services again

You never name a version. The installation guide checks out the ``releases/4.0``
*branch* rather than a version tag, so the branch carries each patch as it is released
and a ``git pull`` is all that moves you between them.

**These steps apply to any 4.0.x patch**, not only this one. What changes between
patches is in the next section.

.. note::

    The service and scheduled task names stopped carrying version numbers in 4.0.0
    precisely so that patch upgrades would not require renaming anything. If you
    upgraded to 4.0.0 from v3.x, your service is called *QATrack+ Web Service* and your
    scheduled task *QATrack+ Django Q Cluster*.

.. include:: _upgrade_4_0_before.rst

Running the upgrade
-------------------

Stop the background services first, so no task runs mid-upgrade:

.. code-block:: bash

    sudo supervisorctl stop django-q2
    sudo service nginx stop

Fetch the new version. If you installed from the ``releases/4.0`` branch — which is
what the installation guide uses — this is a ``pull``, and you do not name a version at
all:

.. code-block:: bash

    cd ~/web/qatrackplus
    git fetch origin
    git pull

.. note::

    If ``git pull`` reports that you are not on a branch, you are on a tag from an
    earlier install. ``git checkout releases/4.0`` once, and every upgrade after that is
    the ``pull`` above.

Update the Python environment. Use the extra that matches your database:

.. code-block:: bash

    cd ~/web/qatrackplus
    source .venv/bin/activate
    uv sync --extra postgres

.. dropdown:: For MySQL
    :color: warning

    .. code-block:: bash

        cd ~/web/qatrackplus
        uv sync --extra mysql

Check the installation before touching the database. This validates your settings
against the new code and is the cheapest way to catch a problem while the services are
still stopped:

.. code-block:: bash

    python manage.py check

Then run the migration step and collect the static files. **There are no migrations in
this release**, so ``migrate`` will report nothing to do — run it anyway, so that a
future release cannot find the database a step behind. ``collectstatic`` is not
optional: this release changes JavaScript and templates.

.. code-block:: bash

    python manage.py migrate
    python manage.py collectstatic

Next, fix the ownership of your ``logs`` and ``qatrack/media`` folders. The 4.0.0
installation guide gave these folders to ``www-data``, but Gunicorn and Django-Q2 run
as the local OS user for QATrack+ services. On an installation set up that way,
uploading an attachment to a Service Event or Test List can fail with a permission
error (`#836 <https://github.com/qatrackplus/qatrackplus/issues/836>`__). These
commands give the folders to your user, keep ``www-data`` as the group so Nginx can
still serve uploaded files, and make new folders inherit that group. You only need to
do this once, and it is safe to run again on an installation that is already correct:

.. code-block:: bash

    cd ~/web/qatrackplus
    sudo chown -R $USER:www-data logs qatrack/media
    sudo find logs qatrack/media -type d -exec chmod 2775 {} +
    sudo find logs qatrack/media -type f -exec chmod 664 {} +

Run these as the same user that runs QATrack+ (the one named in your Supervisor
configuration), not from a ``root`` shell: ``$USER`` would then be ``root``.

Restart:

.. code-block:: bash

    sudo service nginx start
    sudo supervisorctl start django-q2

.. include:: _upgrade_4_0_after.rst
