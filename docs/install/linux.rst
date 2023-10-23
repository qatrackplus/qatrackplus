.. _linux_install_31:

New Installation of QATrack+ v3.1.1 on Ubuntu Linux
===================================================

.. note::

    This guide assumes you have at least a basic level of familiarity with
    Linux and the command line.


This guide is going to walk you through installing everything required to run
QATrack+ on an Ubuntu 20.04 LTS (Focal Fossa) server with Python 3.8, Apache
2.4 as the web server and PostgreSQL 12 (MySQL 8.0) as the database.  The
instructions have also been tested on Ubuntu 18.04 and installation
instructions should be similar on other Ubuntu systems. Similar steps will also
likely work on other Linux distributions but those distributions are not
officially supported or tested.

If you are upgrading an existing QATrack+ installation, please see
one of the following pages:

* :ref:`Upgrading an existing v3.x.y installation to v3.1.1.3
  <linux_upgrading_31>`. 
* :ref:`Upgrading an existing v0.3.0 installation to v3.1.1
  <linux_upgrading_030_to_31>`. 
*  :ref:`Upgrading an existing v0.2.X installation to v3.1.1 <linux_upgrading_02X_to_31>`. 

The steps we will be undertaking are:

.. contents::
    :local:

If you hit an error along the way, stop and figure out why the error is
occuring before proceeding with the next step!  You can seek help on the on the
:mailinglist:`mailing list <>`.

Prerequisites
-------------

These install steps should be done using a regular user account.  They will not
work if you are currently logged in as 'root'.  If you have don't have a
regular user account you should set one up before continuing.

Make sure your existing packages are up to date:

.. code-block:: bash

    sudo apt update
    sudo apt upgrade

You will need to have the `make` command and a few other packages available for
this deployment. Install install them as follows:

.. code-block:: bash

    sudo apt install make build-essential python3-dev python3-tk python3-venv

You will also need the Chrome browser installed for generating PDF reports:

.. code-block:: bash

    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt install ./google-chrome-stable_current_amd64.deb


Installing and configuring Git and checking out the QATrack+ Source Code
------------------------------------------------------------------------

QATrack+ uses the git version controls system.  Ensure you have git installed
with the following command:

.. code-block:: bash

   sudo apt install git

and then configure git (substituting your name and email address!)

.. code-block:: bash

   git config --global user.name "randlet"
   git config --global user.email randy@multileaf.ca

Check out the QATrack+ source code from GitHub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that we have git installed we can proceed to grab the latest version of
QATrack+.  To checkout the code enter the following commands:

.. code-block:: bash

    mkdir -p ~/web
    cd web
    git clone https://github.com/qatrackplus/qatrackplus.git
    cd qatrackplus
    git checkout v3.1.1.3


Installing a Database System
----------------------------

It is *highly* recommended that you choose PostgreSQL for your database,
however it is possible to use MySQL/MariaDB if you need to.

Installing PostgreSQL
~~~~~~~~~~~~~~~~~~~~~

If you do not have an existing database server, you will need to install
PostgreSQL locally. Run the following commands:

.. code-block:: bash

    sudo apt-get install postgresql libpq-dev postgresql-client postgresql-client-common

After that completes, we can create a new database and Postgres user (db
name/user/pwd = qatrackplus31/qatrack/qatrackpass) as follows:

.. code-block:: bash

    cd ~/web/qatrackplus
    sudo -u postgres psql < deploy/postgres/create_db_and_role.sql

And then create a readonly user for the SQL query tool:

.. code-block:: bash

    sudo -u postgres psql < deploy/postgres/create_ro_role.sql


Now edit /etc/postgresql/12/main/pg_hba.conf (use your favourite editor, e.g.
`sudo nano /etc/postgresql/12/main/pg_hba.conf` (note, if you have a different
version of Postgres installed, then you would need to change the 12 in that
path e.g. /etc/postgresql/9.3/main/pg_hba.conf) and scroll down to the bottom
and change `peer` to `md5` for the `local all all` entry so it looks like:

.. code-block:: bash


    # Database administrative login by Unix domain socket
    local   all             postgres                                peer

    # TYPE  DATABASE        USER            ADDRESS                 METHOD

    # "local" is for Unix domain socket connections only
    local   all             all                                     md5
    # IPv4 local connections:
    host    all             all             127.0.0.1/32            md5
    # IPv6 local connections:
    host    all             all             ::1/128                 md5
    # Allow replication connections from localhost, by a user with the
    # replication privilege.
    local   replication     all                                     md5
    host    replication     all             127.0.0.1/32            md5
    host    replication     all             ::1/128                 md5

and restart the pg server:

.. code-block:: bash

    sudo service postgresql restart


Installing MySQL (only required if you prefer to use MySQL over Postgres)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo apt-get install mysql-server libmysqlclient-dev

.. note::

    You should use the InnoDB storage engine for MySQL.  If you are using MySQL
    >= 5.5.5 then it uses InnoDB by default, otherwise if you are using MySQL <
    5.5.5 you need to set the default storage engine to InnoDB:
    https://dev.mysql.com/doc/refman/5.5/en/storage-engine-setting.html


Now we can create and configure a user (db name/user/pwd =
qatrackplus31/qatrack/qatrackpass) and database for QATrack+:

.. code-block:: bash

    # if you set a password during mysql install
    sudo mysql -u root -p < deploy/mysql/create_db_and_role.sql

    # if you didn't
    sudo mysql < deploy/mysql/create_db_and_role.sql


And then create a readonly user for the SQL query tool:


.. code-block:: bash

    # if you  set a password during mysql install
    sudo mysql -u root -p < deploy/mysql/create_ro_role.sql

    # if you didn't
    sudo mysql < deploy/mysql/create_ro_role.sql


Setting up our Python environment (including virtualenv)
--------------------------------------------------------


Check your Python version
~~~~~~~~~~~~~~~~~~~~~~~~~

Version 3.1.1, runs on Python 3.6, 3.7, 3.8, & 3.9 Check your version of
python3 with the command:

.. code-block:: bash

   python3 -V

Which should show the result `Python 3.6.8` or similar.  In order to keep
QATrack+'s Python environment isolated from the system Python, we will run
QATrack+ inside a Python `Virtual Environment`. To create the virtual
environment run the following commands:

Creating our virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: bash

    mkdir -p ~/venvs
    python3 -m venv ~/venvs/qatrack31


Anytime you open a new terminal/shell to work with your QATrack+ installation
you will want to activate your virtual environment.  Do so now like this:

.. code-block:: bash

    source ~/venvs/qatrack31/bin/activate

Your command prompt should now be prefixed with `(qatrack31)`.

It's also a good idea to upgrade `pip` the Python package installer:

.. code-block:: bash

    pip install --upgrade pip

We will now install all the libraries required for QATrack+ with PostgresSQL
(be patient, this can take a few minutes!):

.. code-block:: bash

    cd ~/web/qatrackplus
    pip install -r requirements/postgres.txt

or for MySQL:

.. code-block:: bash

    cd ~/web/qatrackplus
    pip install -r requirements/mysql.txt


Making sure everything is working up to this point
--------------------------------------------------

At this point you can run the QATrack+ test suite to ensure your environment is set up correctly:

.. code-block:: bash

    cd ~/web/qatrackplus
    touch qatrack/local_settings.py
    make test_simple

This should take a few minutes to run and should exit with output that looks
similar to the following:

.. code-block:: bash

    Results (88.45s):

        975 passed
        5 skipped
        32 deselected


Configuration of QATrack+
-------------------------

Next we need to tell QATrack+ how to connect to our database and (optionally)
set some configuration options for your installation.

Create your `local_settings.py` file by copying the example from `deploy/{postgres|mysql}/local_settings.py`:

.. code-block:: bash

    # postgres
    cp deploy/postgres/local_settings.py qatrack/local_settings.py

    # mysql
    cp deploy/mysql/local_settings.py qatrack/local_settings.py


then open the file in a text editor.  There are many available settings and
they are documented within the example file and more completely on :ref:`the
settings page <qatrack-config>`. Directions for :ref:`setting up email
<config_email>`  are also included on that page.

However, the two most important settings are `DATABASES` and `ALLOWED_HOSTS`:
which should be set like the following (switch the `ENGINE` to mysql if
required):

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2', 
            'NAME': 'qatrackplus31',
            'USER': 'qatrack',
            'PASSWORD': 'qatrackpass',
            'HOST': '',
            'PORT': '',
        },
        'readonly': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'qatrackplus31',
            'USER': 'qatrack_reports',
            'PASSWORD': 'qatrackpass',
            'HOST': '',
            'PORT': '',
        }
    }


    # Change XX.XXX.XXX.XX to your servers IP address and/or host name e.g. ALLOWED_HOSTS = ['54.123.45.1', 'yourhostname']
    ALLOWED_HOSTS = ['XX.XXX.XXX.XX']

Once you have got those settings done, we can now test our database connection:

.. code-block:: bash

    python manage.py showmigrations accounts

which should show output like:

.. code-block:: bash

    accounts
        [ ] 0001_initial
        [ ] 0002_activedirectorygroupmap_defaultgroup
        [ ] 0003_auto_20210207_1027

If you were able to connect to your database, we can now create the tables in
our database and install the default data:

.. code-block:: bash

    python manage.py migrate
    python manage.py loaddata fixtures/defaults/*/*


After that completes, we can grant privileges to our readonly database user as
follows:

.. code-block:: bash

    # PostgreSQL
    sudo -u postgres psql < deploy/postgres/grant_ro_rights.sql

    # or MySQL if you set a password during install
    sudo mysql -u root -p -N -B -e "$(cat deploy/mysql/generate_ro_privileges.sql)" > grant_ro_privileges.sql
    sudo mysql -u root -p --database qatrackplus31 < grant_ro_privileges.sql

    # or MySQL if you did not set a password during install
    sudo mysql -N -B -e "$(cat deploy/mysql/generate_ro_privileges.sql)" > grant_ro_privileges.sql
    sudo mysql --database qatrackplus31 < grant_ro_privileges.sql


You also need to create a super user so you can login and begin configuring
your Test Lists:


.. code-block:: bash

    python manage.py createsuperuser

and to create a cachetable in the database:

.. code-block:: bash

    python manage.py createcachetable

and finally we need to collect all our static media files in one location for
Apache to serve:

.. code-block:: bash

    python manage.py collectstatic

If you want to use a translation, you'll need to compile translation messages:

.. code-block:: bash
    
    python manage.py compilemessages


Setting up Django Q
------------------- 

As of version 3.1.0, some features in QATrack+ rely on a separate long running
process which looks after periodic and background tasks like sending out
scheduled notices and reports.  We are going to use 
`Supervisor <http://supervisord.org>`_ to look after running this process
on startup and ensuring it gets restarted if it fails for some reason.

Install supervisor:

.. code-block:: bash

    sudo apt install supervisor


and then set up the Django Q configuration:

.. code-block:: bash

    make supervisor.conf


Lastly, confirm django-q is now running:

.. code-block:: bash

    sudo supervisorctl status

which should result in output like:

.. code-block:: bash

    django-q                         RUNNING   pid 15860, uptime 0:00:05


If supervisor does not show `RUNNING` you can check the error log which 
is located at /var/log/supervisor-django-q.err.log

You can also check on the status of your task cluster at any time like this:

.. code-block:: bash

    source ~/venvs/qatrack31/bin/activate
    cd ~/web/qatrackplus/
    python manage.py qmonitor


Installing Apache web server and mod_wsgi
-----------------------------------------

The next step to take is to install and configure the Apache web server.
Apache and mod_wsgi can be installed with the following commands:

.. code-block:: bash

    sudo apt-get install apache2 apache2-dev libapache2-mod-wsgi-py3 python3-dev


Next, lets make sure Apache can write to our logs and media directories:

.. code-block:: bash

    sudo usermod -a -G www-data $USER
    exec sg www-data newgrp `id -gn` # this refreshes users group memberships without needing to log off/on
    mkdir -p logs
    touch logs/{migrate,debug,django-q,auth}.log
    sudo chown -R www-data:www-data logs
    sudo chown -R www-data:www-data qatrack/media
    sudo chmod ug+rwxs logs
    sudo chmod ug+rwxs qatrack/media

Now we can remove the default Apache config file and copy over the QATrack+ config
file:

.. danger::

    If you already have other sites running using the default config file you
    will want to edit it to include the directives relevant to QATrack+ rather
    than deleting it.  Seek help if you're unsure!

.. code-block:: bash

    make qatrack_daemon.conf
    sudo rm /etc/apache2/sites-enabled/000-default.conf

and finally restart Apache:

.. code-block:: bash

    sudo service apache2 restart


You should now be able to log into your server at http://yourserver/!


Next Steps
----------

* Check the :ref:`the settings page <qatrack-config>` for any available
  customizations you want to add to your QATrack+ installation (don't forget to
  restart Apache after changing any settings!)

* Automate the :ref:`backup of your QATrack+ installation <qatrack_backup>`.

* Read the :ref:`Administration Guide <admin_guide>`, :ref:`User Guide
  <users_guide>`, and :ref:`Tutorials <tutorials>`.


Last Word
---------

There are a lot of steps getting everything set up so don't be discouraged if
everything doesn't go completely smoothly! If you run into trouble, please get
in touch on the :mailinglist:`mailing list <>`.
