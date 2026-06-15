.. _linux_upgrading_40:


Upgrading an existing Linux v3.X.Y installation to v4.0.0
===========================================================

.. note::

    This guide assumes you have at least a basic level of familiarity with
    Linux and the command line.


This guide will walk you through upgrading your existing v3.X.Y installation to
v4.0.0.

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
    git checkout v4.0.0


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
    uv venv --prompt qatrackplus .venv
    source .venv/bin/activate

Your command prompt should now be prefixed with `(qatrackplus)`.

We will now install all the libraries required for QATrack+ with PostgresSQL
(be patient, this can take a few minutes!):

.. code-block:: bash

    cd ~/web/qatrackplus
    uv sync --extra postgres

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

Update Service Configurations and Restart QATrack+
--------------------------------------------------

Because QATrack+ version 4.0.0 completely decouples the web server from the Python interpreter, we are officially migrating away from Apache (`mod_wsgi`) to Nginx and Gunicorn.

First, let's gracefully remove Apache and install Nginx:

.. code-block:: bash

    sudo apt-get remove apache2 libapache2-mod-wsgi-py3
    sudo apt-get install nginx

Now we can generate our new Nginx and Supervisor configurations:

.. code-block:: bash

    cd ~/web/qatrackplus
    source .venv/bin/activate
    make supervisor.conf
    make nginx.conf
    sudo rm -f /etc/nginx/sites-enabled/default

Finally we need to reload Supervisor and restart Nginx:

.. code-block:: console

    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl start django-q2 gunicorn
    sudo service nginx restart


You should now be able to log into your server at http://yourserver/!
