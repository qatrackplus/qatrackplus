.. _linux_upgrading_40:


Upgrading an existing Linux v3.X.Y installation to 4.0.0
===========================================================

.. note::

    This guide assumes you have at least a basic level of familiarity with
    Linux and the command line.


This guide will walk you through upgrading your existing v3.X.Y installation to
4.0.0.

.. warning::

    These upgrade steps should be done using a regular user account. They will not
    work if you are currently logged in as 'root'.

.. contents::
    :local:
    :depth: 2


Take a snapshot
~~~~~~~~~~~~~~~

If your QATrack+ server exists on a virtual machine, now would be a great time
to take a snapshot of your VM in case you need to restore it later!  Consult
with your IT department on how to do this.


Backup your database
~~~~~~~~~~~~~~~~~~~~

It is important you back up your database before attempting to
upgrade. Generate a backup file for your database

.. code-block:: bash

    # postgres
    sudo -u postgres pg_dump -d qatrackplus > backup-3.1.0-$(date -I).sql 

.. dropdown:: For MySQL: Backup Database
    :color: warning

    .. code-block:: bash

        # or for MySQL
        mysqldump --user qatrack --password=qatrackpass qatrackplus > backup-3.1.0-$(date -I).sql 

Backing up your Media folder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is also crucial to back up your uploaded media files before upgrading. Navigate to your QATrack+ installation directory and create a copy or zip archive of the entire ``media`` folder. Save this backup in a safe location:

.. code-block:: bash

    cd ~/web/qatrackplus/qatrack
    tar -czvf media_backup_$(date -I).tar.gz media/


Backing up your local_settings.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your configuration, including database credentials and site-specific settings, is stored in ``local_settings.py``. Create a backup copy of ``local_settings.py`` before proceeding with the upgrade:

.. code-block:: bash

    cp ~/web/qatrackplus/qatrack/local_settings.py ~/web/local_settings_backup_$(date -I).py


Stopping Background Services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before changing branches or creating a new environment, you must stop your background task runner to prevent tasks from executing during the upgrade. 

.. code-block:: bash

    sudo supervisorctl stop django-q2
    sudo service apache2 stop


Make sure your existing packages are up to date
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo apt update
    sudo apt upgrade


Check out version 4.0.0
-------------------------

We can now grab the latest version of QATrack+.  To checkout the code enter the
following commands:

.. code-block:: bash

    cd ~/web/qatrackplus
    git fetch origin
    git checkout releases/4.0

.. dropdown:: Side note: Alternate Tag
    :color: warning

    The ``releases/4.0`` branch is the 4.0 series including its patch releases, so
    upgrading later is ``git fetch`` and ``git pull`` — you never name a version.

    Pinning an exact version with a tag is possible but **not recommended**: a tag is
    immutable, so ``git pull`` will not bring you patches and each upgrade becomes a
    fresh checkout. If you must, the available tags are listed on the
    `releases page <https://github.com/qatrackplus/qatrackplus/releases>`__.


Updating our Python environment
-------------------------------

For version 4.0.0, QATrack+ now uses the `uv` package manager, which will create a new virtual environment inside the `qatrackplus` directory. Your old `~/venvs/qatrack31` directory is no longer needed.

First, install `uv`:

.. code-block:: bash

    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env

Then, create your new virtual environment and activate it:

.. code-block:: bash

    cd ~/web/qatrackplus
    uv venv --python 3.12 --prompt qatrackplus .venv
    source .venv/bin/activate

Your command prompt should now be prefixed with `(qatrackplus)`.

We will now install all the libraries required for QATrack+ with PostgresSQL
(be patient, this can take a few minutes!):

.. code-block:: bash

    cd ~/web/qatrackplus
    uv sync --extra postgres

.. dropdown:: For MySQL: Install Requirements
    :color: warning

    or for MySQL:

    .. code-block:: bash

        cd ~/web/qatrackplus
        uv sync --extra mysql


Performing the migration
------------------------

We can now migrate the tables in our database:

.. code-block:: console

    python manage.py migrate


and then we need to collect all our static media files:

.. code-block:: bash

    python manage.py collectstatic

.. _linux_upgrade_3_reports_0009:

If ``migrate`` stops at ``reports.0009``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Earlier 4.0 releases could stop at ``Applying
reports.0009_Auto_BigAuto_TimeZone_Django42...`` with an error about the
``filters`` column of ``reports_savedreport`` (:issues:`#928 <928>`). It
happened when a saved report's filters had been edited in the 3.x admin, or
when the database had been moved with ``dumpdata``/``loaddata``: either could
leave those filters stored in a format that isn't JSON, and 4.0 needs JSON
there.

Current releases convert those filters as part of the upgrade, so ``migrate``
should simply carry on. If a report's filters can't be read at all, they're
cleared, and ``migrate`` tells you which report it was, with its old filters:

.. code-block:: console

    Saved report 12 ('Monthly summary') had filters that could not be read; they have been
    cleared. Please open the report and set its filters again. They were:
    ...

Once QATrack+ is running, open each report it names and set its filters again.

**If an earlier upgrade attempt already stopped here**, update to a current
release and run ``python manage.py migrate`` again. On PostgreSQL the failed
attempt was rolled back completely, so there's nothing else to do.

.. dropdown:: For MySQL: after a failed attempt
    :color: warning

    MySQL can't roll back changes to the shape of a table, so the failed
    attempt left two new columns behind, ``include_logo`` and ``paper_size``.
    Current releases remove them and add them back automatically. ``migrate``
    mentions it as it goes:

    .. code-block:: console

        Removing column include_logo left in reports_savedreport by an earlier failed run of this
        migration; it is added again below.

    If ``migrate`` still stops at ``reports.0009``, this time with ``(1060,
    "Duplicate column name 'include_logo'")``, remove the two columns
    yourself and run it again. Take a backup first (see above). At this point
    the columns only hold their default values, and ``migrate`` adds them
    straight back:

    .. code-block:: console

        mysql --user qatrack --password qatrackplus \
            -e "ALTER TABLE reports_savedreport DROP COLUMN include_logo, DROP COLUMN paper_size;"
        python manage.py migrate

If none of this matches what you're seeing, please ask on the
:mailinglist:`mailing list <>` and include the full error from ``migrate``.

Update Service Configurations and Restart QATrack+
--------------------------------------------------

Because QATrack+ version 4.0.0 completely decouples the web server from the Python interpreter, we are officially migrating away from Apache (`mod_wsgi`) to Nginx and Gunicorn.

First, let's gracefully remove Apache and install Nginx:

.. code-block:: bash

    sudo apt-get remove apache2 libapache2-mod-wsgi-py3
    sudo apt-get install nginx

Next, update the ownership and permissions of your logs and media directories so that the local OS user for QATrack+ services has ownership while allowing Nginx (``www-data``) read access:

.. code-block:: bash

    cd ~/web/qatrackplus
    sudo chown -R $USER:www-data logs qatrack/media
    sudo find logs qatrack/media -type d -exec chmod 2775 {} +
    sudo find logs qatrack/media -type f -exec chmod 664 {} +

Now we can generate our new Nginx and Supervisor configurations:

.. code-block:: bash

    cd ~/web/qatrackplus
    source .venv/bin/activate
    make supervisor.conf
    sudo rm -f /etc/nginx/sites-enabled/default
    make nginx.conf

Finally we need to reload Supervisor and restart Nginx:

.. code-block:: console

    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl start django-q2 gunicorn
    sudo service nginx restart


You should now be able to log into your server at http://yourserver/!
