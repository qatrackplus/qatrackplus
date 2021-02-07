.. _upgrading_030_to_031:


Upgrading an existing v0.3.0 installation to v0.3.1
===================================================

.. note::

    This guide assumes you have at least a basic level of familiarity with
    Linux and the command line.


.. contents::
    :local:
    :depth: 2


If you hit an error along the way, stop and figure out why the error is
occuring before proceeding with the next step!  You can seek help on the on the
:mailinglist:`mailing list <>`.

Prerequisites
-------------

Take a snapshot
~~~~~~~~~~~~~~~

If your QATrack+ server exists on a virtual machine, now would be a great time
to take a snapshot of your VM in case you need to restore it later!  Consult
with your IT department on how to do this.


Backup your database
~~~~~~~~~~~~~~~~~~~~

It is **extremely** important you back up your database before attempting to
upgrade. Generate a backup file for your database

.. code-block:: console

    # postgres
    pg_dump -U postgres -d qatrackplus > backup-0.3.0-$(date -I).sql 

    # or for MySQL
    mysqldump --user qatrack --password qatrackplus > backup-0.3.0-$(date -I).sql 


Copy your database
~~~~~~~~~~~~~~~~~~

In order to make reverting to your prior configuration simpler, it is
recommended to clone your existing database by creating a new database,
restoring your backup and then perform the upgrade on it instead.  This will
also confirm your backup step above worked.

.. code-block:: console

    # postgres (# it's ok if you see an error "role "qatrack" already exists)
    psql -U postgres -c "CREATE DATABASE qatrackplus031;"
    psql -U postgres -d qatrackplus031 < backup-0.3.0-$(date -I).sql
    psql -U postgres -c "CREATE USER qatrack with PASSWORD 'qatrackpass';"
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE qatrackplus031 to qatrack;"

    # or for MySQL
    mysqldump --user=qatrack --password=qatrackplus --database qatrackplus > backup-0.3.0-$(date -I).sql 
    sudo mysql -p -e "CREATE DATABASE qatrackplus031;"
    sudo mysql -p --database=qatrackplus031< backup-0.3.0-$(date -I).sql
    sudo mysql -p -e "GRANT ALL ON qatrackplus031.* TO 'qatrack'@'localhost';"


Now confirm your restore worked:

.. code-block:: console

    # postgres: Should show Count=1234 or similar
    PGPASSWORD=qatrackpass psql -U qatrack -d qatrackplus031 -c "SELECT COUNT(*) from qa_testlistinstance;"

    # mysql: Should show Count=1234 or similar
    sudo mysql -p --database qatrackplus031 -e "SELECT COUNT(*) from qa_testlistinstance;"


Check your Python version
~~~~~~~~~~~~~~~~~~~~~~~~~

Version 0.3.1, runs on Python 3.6, 3.7, 3.8, & 3.9 Check your version of
python3 with the command:

.. code-block:: console

   python3 -V

if that shows a version of Python lower than 3.6 then you will need to install
a more up to date version of Python before proceeding.

Make sure your existing packages are up to date
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    sudo apt update
    sudo apt upgrade

You will also need the Chromium browser installed for generating PDF reports:

.. code-block:: console

    sudo apt install chromium-browser


Check out the latest version of QATrack+
----------------------------------------

We can now grab the latest version of QATrack+.  To checkout the code enter the
following commands:

.. code-block:: console

    cd ~/web/qatrackplus
    git fetch origin
    git checkout v0.3.1


Setting up our Python environment (including virtualenv)
--------------------------------------------------------

We will create a new `Virtual Environment` in order to make it simpler to
revert to your old environment if required.  To create the virtual environment
run the following commands:

.. code-block:: console

    python3 -m venv ~/venvs/qatrack31

Anytime you open a new terminal/shell to work with your QATrack+ installation
you will want to activate your virtual environment.  Do so now like this:

.. code-block:: console

    source ~/venvs/qatrack31/bin/activate

Your command prompt should now be prefixed with `(qatrack31)`.

It's also a good idea to upgrade `pip` the Python package installer:

.. code-block:: console

    pip install --upgrade pip

We will now install all the libraries required for QATrack+ with PostgresSQL
(be patient, this can take a few minutes!):

.. code-block:: console

    cd ~/web/qatrackplus
    pip install -r requirements/postgres.txt

or for MySQL:

.. code-block:: console

    cd ~/web/qatrackplus
    pip install -r requirements/mysql.txt


Configuration of QATrack+
~~~~~~~~~~~~~~~~~~~~~~~~~

Next we need to tell QATrack+ how to connect to our newly restored database.

Edit your `qatrack/local_settings.py` and adjust your `DATABASE` setting so it
looks similar to this:

.. code-block:: python

    # for postgres
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'qatrackplus031',
            'USER': 'qatrack',
            'PASSWORD': 'qatrackpass',
            'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',  # Set to empty string for default. Not used with sqlite3.
        },
        'readonly': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'qatrackplus031',
            'USER': 'qatrack_reports',
            'PASSWORD': 'qatrackpass',
            'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',  # Set to empty string for default. Not used with sqlite3.
        }
    }


    # for mysql
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'qatrackplus031',
            'USER': 'qatrack',
            'PASSWORD': 'qatrackpass',
            'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',  # Set to empty string for default. Not used with sqlite3.
        },
        'readonly': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'qatrackplus031',
            'USER': 'qatrack_reports',
            'PASSWORD': 'qatrackpass',
            'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',  # Set to empty string for default. Not used with sqlite3.
        }
    }


Once you have got those settings done, we can now test our database connection:

.. code-block:: console

    python manage.py showmigrations accounts

which should show output like:

.. code-block:: console

    accounts
        [ ] 0001_initial
        [ ] 0002_activedirectorygroupmap_defaultgroup

If you were able to connect to your database, we can now migrate the tables in
our database.

.. code-block:: console

    python manage.py migrate


After that completes, we can create a readonly database user (db name/user/pwd
= qatrack_reports/qatrack_reports/qatrackpass) as follows:

.. code-block:: console

    # PostgreSQL
    sudo -u postgres psql < deploy/postgres/create_ro_db_and_role.sql

    # or MySQL if you set a password during install
    sudo mysql -u root -p -N -B -e "$(cat deploy/mysql/generate_ro_privileges.sql)" > grant_ro_priv.sql
    sudo mysql -u root -p --database qatrackplus < generate_ro_privileges.sql

    # or MySQL if you did not set a password during install
    sudo mysql < deploy/mysql/create_ro_db_and_role.sql
    sudo mysql --database qatrackplus < generate_ro_privileges.sql


You also need to create a cachetable in the database:

.. code-block:: console

    python manage.py createcachetable

and finally we need to collect all our static media files in one location for
Apache to serve:

.. code-block:: console

    python manage.py collectstatic


Setting up Django Q
~~~~~~~~~~~~~~~~~~~~

As of version 0.3.1, some features in QATrack+ rely on a separate long running
process which looks after periodic and background tasks like sending out
scheduled notices and reports.  We are going to use 
`Supervisor <http://supervisord.org>`_ to look after running this process
on startup and ensuring it gets restarted if it fails for some reason.

Install supervisor:

.. code-block:: console

    sudo apt install supervisor


and then set up the Django Q configuration:

.. code-block:: console

    make supervisor.conf


Lastly, confirm django-q is now running:

.. code-block:: console

    sudo supervisorctl status

which should result in output like:

.. code-block:: console

    django-q                         RUNNING   pid 15860, uptime 0:00:05


If supervisor does not show `RUNNING` you can check the error log which 
is located at /var/log/supervisor-django-q.err.log

You can also check on the status of your task cluster at any time like this:

.. code-block:: console

    source ~/virtualenvs/qatrack31/bin/activate
    cd ~/web/qatrackplus/
    python manage.py qmonitor


Setting File Permissions for Apache
-----------------------------------

Next, lets make sure Apache can write to our logs and media directories:

.. code-block:: console

    sudo usermod -a -G www-data $USER
    exec sg www-data newgrp `id -gn` # this refreshes users group memberships without needing to log off/on
    mkdir -p logs
    touch logs/{migrate,debug,django-q,auth}.log
    sudo chown -R www-data:www-data logs
    sudo chown -R www-data:www-data qatrack/media
    sudo chmod ug+rwxs logs
    sudo chmod ug+rwxs qatrack/media

Now we can update our default Apache config file so that it points to the
correct virtualenv.  Edit `/etc/apache2/sites-available/qatrack.conf` and
find the `WSGIDaemonProcess` line and update the `python-home` variable so
that it points to `/venvs/qatrack31`:

.. code-block:: apache

    WSGIDaemonProcess qatrackplus python-home=/home/YOURUSERNAMEHERE/venvs/qatrack31 python-path=/home/YOURUSERNAMEHERE/web/qatrackplus

and finally restart Apache:

.. code-block:: console

    sudo service apache2 restart


You should now be able to log into your server at http://yourserver/!


What Next
---------

* Make sure you have read the release notes for version 0.3.1 carefully.  There
  are some new :ref:`settings <qatrack-config>` you may want to adjust.

* Since the numpy, scipy, pylinac, pydicom, & matplotlib libraries have been
  updated, some of your calculation procedures may need to be adjusted to
  restore functionality.

* Adjust your :ref:`backup script <qatrack_backup>` so that it is now backing
  up the `qatrackplus031` database instead of the version 0.3.0 database!


Last Word
---------

There are a lot of steps getting everything set up so don't be discouraged if
everything doesn't go completely smoothly! If you run into trouble, please get
in touch on the :mailinglist:`mailing list <>`.
