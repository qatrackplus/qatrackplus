Installing and Deploying QATrack+ on Ubuntu Linux
=================================================

*This guide assumes you have at least a basic level of familiarity with Linux
and the command line.*

.. contents::
    :local:
    :depth: 1


New Installation
----------------

This guide is going to walk you through installing everything required to run
QATrack+ on an Ubuntu 16.04 (Xenial Xerus) server with Python 3.5, Apache 2.4
as the web server and PostgreSQL 9.5 (MySQL 5.5)  as the database. Installation
instructions should be similar on other Linux systems.

The steps we will be undertaking are:

.. contents::
    :local:

If you hit an error along the way, stop and figure out why the error is
occuring before proceeding with the next step! 

Prerequisites
.............

You will need to have the `make` command available for this deployment. Install it as follows:

.. code-block:: bash

    sudo apt update
    sudo apt install make


Installing a Database System
............................

It is highly recommended that you choose PostgreSQL for your database, however
it is possible to use MySQL/MariaDB if you need to.

Installing PostgreSQL
^^^^^^^^^^^^^^^^^^^^^

To install PostgreSQL run the following commands:

.. code-block:: bash

    sudo apt install postgresql libpq-dev postgresql-client postgresql-client-common

After that completes, we can create a new Postgres user (db/user/pwd = qatrackplus/qatrack/qatrackpass) as follows:

.. code-block:: bash

    sudo -u postgres psql < db/postgres/create_db_and_role.sql


Now edit /etc/postgresql/9.3/main/pg_hba.conf and scroll down to the
bottom and change the two instances of `peer` to `md5` so it looks
like:

.. code-block:: bash

    # Database administrative login by Unix domain socket
    local   all             postgres                                md5

    # TYPE  DATABASE        USER            ADDRESS                 METHOD

    # "local" is for Unix domain socket connections only
    local   all             all                                     md5
    # IPv4 local connections:
    host    all             all             127.0.0.1/32            md5
    # IPv6 local connections:
    host    all             all             ::1/128                 md5

and restart the pg server:

.. code-block:: bash

    sudo service postgresql restart


Installing MySQL
^^^^^^^^^^^^^^^^

.. code-block:: bash

    sudo apt-get install mysql-server libmysqlclient-dev


Now we can create and configure a user and database for QATrack+:

.. code-block:: bash

    sudo -u postgres psql < db/mysql/create_db_and_role.sql


Installing and configuring Git
..............................

QATrack+ uses the git version controls system.  Ensure you have git installed with
the following command:

.. code-block:: bash

   sudo apt update
   sudo apt install git

and then configure git (substituting your name and email address!)

.. code-block:: bash

   git config --global user.name "randlet"
   git config --global user.email randle.taylor@gmail.com

Check out the QATrack+ source code from BitBucket
.................................................

Now that we have git installed we can proceed to grab the latest version of
QATrack+.  To checkout the code enter the following commands:

.. code-block:: bash

    mkdir -p ~/web
    cd web
    git clone https://bitbucket.org/tohccmedphys/qatrackplus.git


Check your Python version
.........................

Unlike previous versions of QATrack+, version 0.3.0, runs on Python 3.4+ rather
than Python 2.7. Check your version of python3 with the command:

.. code-block:: bash

   python3 -V

Which should show the result `Python 3.5.2` or similar.  QATrack+ v0.3.0 is
tested on Python versions 3.4.X, 3.5.X, & 3.6.X.


Setting up our Python environment (including virtualenv)
........................................................

In order to keep QATrack+'s Python environment isolated from the system
Python, we will run QATrack+ inside a Python `Virtual Environment`. To create
the virtual environment run the following commands:


.. code-block:: bash

    sudo apt install python3-venv
    mkdir -p ~/venvs
    python3 -m venv ~/venvs/qatrack3


Anytime you open a new terminal/shell to work with your QATrack+ installation
you will want to activate your virtual environment.  Do so now like this:

.. code-block:: bash

    source ~/venvs/qatrack3/bin/activate

Your command prompt should now be prefixed with `(qatrack3)`.

It's also a good idea to upgrade `pip` the Python package installer:

.. code-block:: bash

    pip install --upgrade pip

We will now install all the libraries required for QATrack+ with PostgresSQL:

.. code-block:: bash

    cd ~/web/qatrackplus
    pip install -r requirements.pgsql.txt

or for MySQL:

.. code-block:: bash

    cd ~/web/qatrackplus
    pip install -r requirements.mysql.txt


Making sure everything is working up to this point
..................................................

At this point you can run the QATrack+ test suite to ensure your environment is set up correctly:

.. code-block:: bash

    cd ~/web/qatrackplus
    make test_simple

This should take a few minutes to run and should exit with output that looks
similar to the following:

.. code-block:: bash

    Results (88.45s):
        440 passed



Installing Apache web server and mod_wsgi
.........................................

The next step to take is to install and configure the Apache web server.
Apache and mod_wsgi can be installed with the following commands:

.. code-block:: bash

    sudo apt-get install apache2 apache2-dev libapache2-mod-wsgi-py3 python3-dev

Now we can remove the default Apache config file and copy over the QATrack+ config
file:

.. note:

    If you already have other sites running using the 000-default.conf file you will
    want to edit it to include the directives relevant to QATrack+ rather than deleting
    it.  Seek help if you're unsure!

.. code-block:: bash

    make qatrack_daemon.conf
    sudo rm /etc/apache2/sites-enabled/000-default.conf
    sudo cp ~/web/qatrackplus/qatrack.conf /etc/apache2/sites-available/qatrack.conf
    sudo ln -s /etc/apache2/sites-available/qatrack.conf /etc/apache2/sites-enabled/qatrack.conf
    sudo service apache2 restart
    sudo usermod -a -G www-data $USER



Final configuration of QATrack+
...............................

Next we need to tell QATrack+ how to connect to our database and (optionally)
set some configuration options for your installation.

Create your `local_settings.py` file by copying the example from `deploy/local_settings.py`:

.. code-block:: bash

    cp deploy/local_settings.py .

then open the file in a text editor.  There are many available settings and
they are documented within the example file and more completely on :ref:`the
settings page <qatrack-config>`.

However, the two most important settings are
`DATABASES` and `ALLOWED_HOSTS`: which should be set like the following (switch
the `ENGINE` to mysql if required):

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3'
            'NAME': 'qatrackplus',                      # Or path to database file if using sqlite3.
            'USER': 'qatrack',                      # Not used with sqlite3.
            'PASSWORD': 'qatrackpass',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }


    ALLOWED_HOSTS = ['XX.XXX.XXX.XX']  # Set to your server IP address (or *)!

Once you have got those settings done, we can now create the tables in our
database and install the default data:


.. code-block:: bash

    python manage.py migrate
    python manage.py loaddata fixtures/defaults/*/*

and we also need to collect all our static media files in one location for
Apache to serve and then restart Apache:

.. code-block:: bash

    python manage.py collectstatic
    sudo service apache2 restart


Last Word
.........

There are a lot of steps getting everything set up so don't be discouraged if
everything doesn't go completely smoothly! If you run into trouble, please get
in touch with me on the :mailinglist:`mailing list <>` and I can help you out.

R. Taylor



Upgrading from version 0.2.8
----------------------------

In order to upgrade from version 0.2.8 you must first uprade to version 0.2.9.
If you hit an error along the way, stop and figure out why the error is
occuring before proceeding with the next step! 

.. contents::
    :local:


Activate your virtual environment
.................................

As usual, you will first want to activate your virtual environment:

.. code-block:: bash

    source ~/venvs/qatrack/bin/activate


Backing up your database
........................

It is **extremely** important you back up your database before attempting
to upgrade. You can either generate a json dump of your database (possibly slow!):

.. code-block:: bash

    python manage.py dumpdata > backup-0.2.8-$(date -I).json

and/or by using your database to dump a backup file:

.. code-block:: bash

    pg_dump -U <username> --password <dbname> > backup-0.2.8-$(date -I).sql   # e.g. pg_dump -U qatrack --password qatrackdb > backup-0.2.8-$(date -I).sql

    # or for MySQL

    mysqldump --user <username> --password <dbname> > backup-0.2.8-$(date -I).sql  # e.g. mysqldump --user qatrack --password qatrackdb > backup-0.2.8-$(date -I).sql


Checking out version 0.2.9
..........................

First we must check out the code for version 0.2.9:

.. code-block:: bash

    git fetch origin
    git checkout v0.2.9.1

Update your existing virtual environment
........................................

.. code-block:: bash

    pip install -r requirements/base.txt


Migrate your database
.....................

The next step is to migrate the 0.2.8 database schema to 0.2.9:

.. code-block:: bash

    python manage.py migrate

Assuming that proceeds without errors you can proceed to `Upgrading from
version 0.2.9` below.


Upgrading from version 0.2.9
----------------------------

The steps below will guide you through upgrading a version 0.2.9 installation
to 0.3.0.  If you hit an error along the way, stop and figure out why the error
is occuring before proceeding with the next step! 

.. contents::
    :local:

Verifying your Python 3 version
...............................

Unlike QATrack+ v0.2.9 which runs on Python 2.7, QATrack+ 0.3.0 only runs on
Python version 3.4, 3.5 or, 3.6.  You will need to ensure you have one of those
Python versions installed:

.. code-block:: bash

    python3 -V
    # should result in e.g.
    Python 3.5.2

If you don't see either Python 3.4.X, 3.5.X or, 3.6.X then you will need to
install Python 3 on your system (beyond the scope of this document).


Backing up your database
........................

It is **extremely** important you back up your database before attempting
to upgrade. You can either generate a json dump of your database (possibly slow!):

.. code-block:: bash

    source ~/venvs/qatrack/bin/activate
    python manage.py dumpdata > backup-0.2.9-$(date -I).json
    deactivate

and/or by using your database to dump a backup file:

.. code-block:: bash

    pg_dump -U <username> --password <dbname> > backup-0.2.8-$(date -I).sql   # e.g. pg_dump -U qatrack --password qatrackdb > backup-0.2.9-$(date -I).sql

    # or for MySQL

    mysqldump --user <username> --password <dbname> > backup-$(date -I).sql  # e.g. mysqldump --user qatrack --password qatrackdb > backup-0.2.9-$(date -I).sql


Checking out version 0.3.0
..........................

First we must check out the code for version 0.3.0:

.. code-block:: bash

    git checkout master
    git pull origin master


Create and activate your new virtual environment
................................................

We need to create a new virtual environment with the Python 3 interpreter:

.. code-block:: bash

    virtualenv -P $(which python3) ~/venvs/qatrack3
    source ~/venvs/qatrack3/bin/activate


and we can then install the required python libraries:

.. code-block:: bash

    pip install -r requirements.postgres.txt  # or requirements.mysql.txt


Migrate your database
.....................

The next step is to update the v0.2.9 schema to v0.3.0

.. code-block:: bash

    python manage.py migrate --fake-iniital


Check the migration log
.......................

During the migration above you may have noticed some warnings like:


    | Note: if any of the following tests process binary files (e.g. images, dicom files etc) rather than plain text, you must edit the calculation and replace 'FILE' with 'BIN_FILE'. Tests:
    |
    | Test name 1 (test-1) 
    | Test name 2 (test-2) 
    | ...

This data is also available in the `logs/migrate.log` file.  Because the way
Python handles text encodings / files has changed in Python 3, you will
need to update any upload test that handles binary data by changing the
`FILE` reference in the calculation procedure to `BIN_FILE`. For example change:

.. code-block:: python

    data = FILE.read()
    # do something with data

to:

.. code-block:: python

    data = BIN_FILE.read()
    # do something with data


Update your local_settings.py file
..................................

Now is a good time to review your `local_settings.py` file. There are
a few new settings that you may want to configure.  The settings are
documented in :ref:`the settings page <qatrack-config>`.


Update your Apache configuration
................................


Since we are now using a different Python virtual environment we need to update
the `WSGIPythonHome` variable.  Open your Apache config file (either
/etc/apache2/sites-available/default.conf or /etc/apache2/httpd.conf) and set
the virtualenv path correctly:

.. code-block:: apache

    WSGIPythonHome /home/YOURUSERNAME/venvs/qatrack3

and then restart Apache:

.. code-block:: bash

    sudo service apache2 restart


Last Word
.........

There are a lot of steps getting everything set up so don't be discouraged if
everything doesn't go completely smoothly! If you run into trouble, please get
in touch with me on the :mailinglist:`mailing list <>` and I can help you out.

R. Taylor
