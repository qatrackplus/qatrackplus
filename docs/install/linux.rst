Installing and Deploying QATrack+ on Ubuntu Linux
=================================================


.. note::

    This guide assumes you have at least a basic level of familiarity with
    Linux and the command line.


.. contents::
    :local:
    :depth: 1


New Installation
----------------

This guide is going to walk you through installing everything required to run
QATrack+ on an Ubuntu 18.04 LTS (Bionic Beaver) server with Python 3.6, Apache
2.4 as the web server and PostgreSQL 10 (MySQL 5.5) as the database.
Installation instructions should be similar on other Linux systems. If you are
upgrading an existing installation, please see the sections below on upgrading
from v0.2.8 or v0.2.9.

The steps we will be undertaking are:

.. contents::
    :local:

If you hit an error along the way, stop and figure out why the error is
occuring before proceeding with the next step!

Prerequisites
~~~~~~~~~~~~~

Make sure your existing packages are up to date:

.. code-block:: console

    sudo apt-get update
    sudo apt-get upgrade

You will need to have the `make` command and a few other packages available for
this deployment. Install install them as follows:

.. code-block:: console

    sudo apt-get install make build-essential python3-dev python3-tk


Installing and configuring Git
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ uses the git version controls system.  Ensure you have git installed with
the following command:

.. code-block:: console

   sudo apt-get install git

and then configure git (substituting your name and email address!)

.. code-block:: console

   git config --global user.name "randlet"
   git config --global user.email randy@multileaf.ca

Check out the QATrack+ source code from BitBucket
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that we have git installed we can proceed to grab the latest version of
QATrack+.  To checkout the code enter the following commands:

.. code-block:: console

    mkdir -p ~/web
    cd web
    git clone https://bitbucket.org/tohccmedphys/qatrackplus.git


Installing a Database System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is *highly* recommended that you choose PostgreSQL for your database,
however it is possible to use MySQL/MariaDB if you need to.

Installing PostgreSQL
.....................

If you do not have an existing database server, you will need to install
PostgreSQL locally. Run the following commands:

.. code-block:: console

    sudo apt-get install postgresql libpq-dev postgresql-client postgresql-client-common

After that completes, we can create a new Postgres user (db name/user/pwd =
qatrackplus/qatrack/qatrackpass) as follows:

.. code-block:: console

    cd ~/web/qatrackplus
    sudo -u postgres psql < deploy/postgres/create_db_and_role.sql


Now edit /etc/postgresql/10/main/pg_hba.conf (use your favourite editor, e.g.
`sudo nano /etc/postgresql/10/main/pg_hba.conf`, note, if you have a different
version of Postgres installed, then you would need to change the 10 in that
path e.g. /etc/postgresql/9.3/main/pg_hba.conf) and scroll down to the bottom
and change the instances of `peer` to `md5` so it looks like:

.. code-block:: console


    # Database administrative login by Unix domain socket
    local   all             postgres                                md5

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

.. code-block:: console

    sudo service postgresql restart


Installing MySQL (only required if you prefer to use MySQL over Postgres)
.........................................................................

.. code-block:: console

    sudo apt-get install mysql-server libmysqlclient-dev

.. note::

    You should use the InnoDB storage engine for MySQL.  If you are using MySQL
    >= 5.5.5 then it uses InnoDB by default, otherwise if you are using MySQL <
    5.5.5 you need to set the default storage engine to InnoDB:
    https://dev.mysql.com/doc/refman/5.5/en/storage-engine-setting.html


Now we can create and configure a user (db name/user/pwd =
qatrackplus/qatrack/qatrackpass) and database for QATrack+:


.. code-block:: bash

    # if you  set a password during mysql install
    sudo mysql -u root -p < deploy/mysql/create_db_and_role.sql

    # if you didn't
    sudo mysql < deploy/mysql/create_db_and_role.sql


Setting up our Python environment (including virtualenv)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Check your Python version
.........................

Unlike previous versions of QATrack+, version 0.3.0, runs on Python 3.5+ rather
than Python 2.7. Check your version of python3 with the command:

.. code-block:: console

   python3 -V

Which should show the result `Python 3.5.2` or similar.  QATrack+ v0.3.0 is
tested on Python versions 3.5.X, & 3.6.X but 3.4.x should also work.
In order to keep QATrack+'s Python environment isolated from the system
Python, we will run QATrack+ inside a Python `Virtual Environment`. To create
the virtual environment run the following commands:

Creating our virtual environment
................................


.. code-block:: console

    sudo apt-get install python3-venv  # use python3.4-venv on Ubuntu 14.04
    mkdir -p ~/venvs
    python3 -m venv ~/venvs/qatrack3


Anytime you open a new terminal/shell to work with your QATrack+ installation
you will want to activate your virtual environment.  Do so now like this:

.. code-block:: console

    source ~/venvs/qatrack3/bin/activate

Your command prompt should now be prefixed with `(qatrack3)`.

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


Making sure everything is working up to this point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At this point you can run the QATrack+ test suite to ensure your environment is set up correctly:

.. code-block:: console

    cd ~/web/qatrackplus
    make test_simple

This should take a few minutes to run and should exit with output that looks
similar to the following:

.. code-block:: console

    Results (88.45s):
        440 passed
          2 skipped
         11 deselected



Installing Apache web server and mod_wsgi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

    If you are on Ubuntu 14.04 please complete this section then complete the
    "Installing Apache on Ubuntu 14.04" section below!

The next step to take is to install and configure the Apache web server.
Apache and mod_wsgi can be installed with the following commands:

.. code-block:: console

    sudo apt-get install apache2 apache2-dev libapache2-mod-wsgi-py3 python3-dev


Next, lets make sure Apache can write to our logs and media directory:

.. code-block:: console

    sudo usermod -a -G www-data $USER
    mkdir -p logs
    touch logs/{migrate,debug}.log
    chmod ug+rwx logs
    chmod ug+rwx qatrack/media
    chmod a+rw logs/{migrate,debug}.log

Now we can remove the default Apache config file and copy over the QATrack+ config
file:

.. danger::

    If you already have other sites running using the default config file you
    will want to edit it to include the directives relevant to QATrack+ rather
    than deleting it.  Seek help if you're unsure!

.. code-block:: console

    make qatrack_daemon.conf
    sudo rm /etc/apache2/sites-enabled/000-default.conf


Installing Apache on Ubuntu 14.04
.................................

The process for installing Apache on Ubuntu 14.04 is a bit more complicated. If
you can upgrade to 18.04 it is recommended you do so. Otherwise, read on (ref
https://askubuntu.com/a/569551).

First uninstall the existing mod-wsgi-py3 package and make sure apache-dev is installed:

.. code-block:: console

    sudo apt-get remove libapache2-mod-wsgi-py3
    sudo apt-get install apache2-dev
    source ~/venvs/qatrack3/bin/activate
    pip install mod_wsgi

Now install mod_wsgi into Apache:

.. code-block:: console

    sudo ~/venvs/qatrack3/bin/mod_wsgi-express install-module

which will result in two lines like:

.. code-block:: console

    LoadModule wsgi_module "/usr/lib/apache2/modules/mod_wsgi-py34.cpython-34m.so"
    WSGIPythonHome "/home/ubuntu/venvs/qatrack3"


Write the first line to `/etc/apache2/mods-available/wsgi_express.load` and the
second line to `/etc/apache2/mods-available/wsgi_express.conf`:

.. code-block:: console

    echo 'LoadModule wsgi_module "/usr/lib/apache2/modules/mod_wsgi-py34.cpython-34m.so"' | sudo tee --append /etc/apache2/mods-available/wsgi_express.conf
    echo 'WSGIPythonHome "/home/ubuntu/venvs/qatrack3"' | sudo tee --append /etc/apache2/mods-available/wsgi_express.load

Now enable the wsgi_express module and restart Apache:

.. code-block:: console

    sudo a2enmod wsgi_express
    sudo service apache2 restart


Final configuration of QATrack+
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next we need to tell QATrack+ how to connect to our database and (optionally)
set some configuration options for your installation.

Create your `local_settings.py` file by copying the example from `deploy/{postgres|mysql}/local_settings.py`:

.. code-block:: console

    cp deploy/postgres/local_settings.py qatrack/local_settings.py
    # or #
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


.. code-block:: console

    python manage.py migrate
    python manage.py loaddata fixtures/defaults/*/*

You also need to create a super user so you can login and begin configuring
your Test Lists:


.. code-block:: console

    python manage.py createsuperuser


and finally we need to collect all our static media files in one location for
Apache to serve and then restart Apache:

.. code-block:: console

    python manage.py collectstatic
    sudo service apache2 restart


You should now be able to log into your server at http://yourserver/.

What Next
~~~~~~~~~

* Check the :ref:`the settings page <qatrack-config>` for any available
  customizations you want to add to your QATrack+ installation (don't forget to
  restart Apache after changing any settings!)

* Automate the :ref:`backup of your QATrack+ installation <qatrack_backup>`.

* Read the :ref:`Administration Guide <admin_guide>`, :ref:`User Guide
  <users_guide>`, and :ref:`Tutorials <tutorials>`.


Last Word
~~~~~~~~~

There are a lot of steps getting everything set up so don't be discouraged if
everything doesn't go completely smoothly! If you run into trouble, please get
in touch with me on the :mailinglist:`mailing list <>` and I can help you out.



Upgrading from version 0.2.8
----------------------------

In order to upgrade from version 0.2.8 you must first uprade to version 0.2.9.
If you hit an error along the way, stop and figure out why the error is
occuring before proceeding with the next step!  If you want assistance with the
process, please post to to the :mailinglist:`Mailing List <>`.

.. contents::
    :local:


Activate your virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As usual, you will first want to activate your existing virtual environment:

.. code-block:: console

    source ~/venvs/qatrack/bin/activate


Backing up your database
~~~~~~~~~~~~~~~~~~~~~~~~

It is **extremely** important you back up your database before attempting to
upgrade. You can either use your database to dump a backup file:

.. code-block:: console

    pg_dump -U <username> --password <dbname> > backup-0.2.8-$(date -I).sql   # e.g. pg_dump -U qatrack --password qatrackdb > backup-0.2.8-$(date -I).sql

    # or for MySQL

    mysqldump --user <username> --password <dbname> > backup-0.2.8-$(date -I).sql  # e.g. mysqldump --user qatrack --password qatrackdb > backup-0.2.8-$(date -I).sql

or generate a json dump of your database (possibly extremely slow!):

.. code-block:: console

    cd ~/web/qatrackplus
    python manage.py dumpdata --natural > backup-0.2.8-$(date -I).json


Checking out version 0.2.9
~~~~~~~~~~~~~~~~~~~~~~~~~~

First we must check out the code for version 0.2.9:

.. code-block:: console

    git fetch origin
    git checkout v0.2.9.1

.. warning::

    If you get any errors using git (e.g. trying to check out v0.2.9.1) that
    you don't know how to handle, please stop and get help!


Update your existing virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There were a number of changes in dependencies for version 0.2.9 so we need to
update our virtual env:

.. code-block:: console

    pip install --upgrade pip
    pip install -r requirements/base.txt


Migrate your database
~~~~~~~~~~~~~~~~~~~~~

.. note::

    You should use the InnoDB storage engine for MySQL.  If you are using MySQL
    >= 5.5.5 then it uses InnoDB by default, otherwise if you are using MySQL <
    5.5.5 you need to set the default storage engine to InnoDB:
    https://dev.mysql.com/doc/refman/5.5/en/storage-engine-setting.html


The next step is to migrate the 0.2.8 database schema to 0.2.9:

.. code-block:: console

    python manage.py syncdb
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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unlike QATrack+ v0.2.9 which runs on Python 2.7, QATrack+ 0.3.0 only runs on
Python version 3.5 or 3.6 (and probably 3.4!).  You will need to ensure you have one of those
Python versions installed:

.. code-block:: console

    python3 -V
    # should result in e.g.
    Python 3.5.2

If you don't see either Python 3.4.X, 3.5.X or, 3.6.X then you will need to
install Python 3 on your system (beyond the scope of this document).


Backing up your database
~~~~~~~~~~~~~~~~~~~~~~~~

It is **extremely** important you back up your database before attempting to
upgrade. You can either use your database to dump a backup file:

.. code-block:: console

    pg_dump -U <username> --password <dbname> > backup-0.2.9-$(date -I).sql   # e.g. pg_dump -U qatrack --password qatrackdb > backup-0.2.9-$(date -I).sql

    # or for MySQL

    mysqldump --user <username> --password <dbname> > backup-0.2.9-$(date -I).sql  # e.g. mysqldump --user qatrack --password qatrackdb > backup-0.2.9-$(date -I).sql

or generate a json dump of your database (possibly extremely slow!):

.. code-block:: console

    source ~/venvs/qatrack/bin/activate
    python manage.py dumpdata --natural > backup-0.2.9-$(date -I).json
    deactivate


Checking out version 0.3.0
~~~~~~~~~~~~~~~~~~~~~~~~~~

First we must check out the code for version 0.3.0:

.. code-block:: console

    git fetch origin
    git checkout v0.3.0.15


Create and activate your new virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you currently have a virtualenv activated, deactivate it with the
`deactivate` command:

.. code-block:: console

    deactivate

We need to create a new virtual environment with the Python 3 interpreter:

.. code-block:: console

    sudo apt-get install python3-venv
    python3 -m venv ~/venvs/qatrack3
    source ~/venvs/qatrack3/bin/activate

and we can then install the required python libraries:

.. code-block:: console

    pip install -r requirements/postgres.txt  # or requirements/mysql.txt


Migrate your database
~~~~~~~~~~~~~~~~~~~~~

.. note::

    You should use the InnoDB storage engine for MySQL.  If you are using MySQL
    >= 5.5.5 then it uses InnoDB by default, otherwise if you are using MySQL <
    5.5.5 you need to set the default storage engine to InnoDB:
    https://dev.mysql.com/doc/refman/5.5/en/storage-engine-setting.html

The next step is to update the v0.2.9 schema to v0.3.0

.. code-block:: console

    python manage.py migrate --fake-initial

and load some initial service log data:

.. code-block:: console

    python manage.py loaddata fixtures/defaults/units/*
    python manage.py loaddata fixtures/defaults/service_log/*


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


You may have also seen warnings like:


    |  The test named 'yourtestname' with ID=1234 needs to be updated to be
    |  compatible with Python 3.


While most Test calculation procedures will be compatible with both Python 2
and Python 3, there have been some syntactical changes in the language which
may require you to update a calculation procedure to be Python 3 compatible.


Update your local_settings.py file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now is a good time to review your `local_settings.py` file. There are
a few new settings that you may want to configure.  The settings are
documented in :ref:`the settings page <qatrack-config>`.


Update your Apache configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, lets make sure Apache can write to our logs and media directory:

.. code-block:: console

    sudo usermod -a -G www-data $USER
    mkdir -p logs
    touch logs/{migrate,debug}.log
    chmod ug+rwx logs
    chmod ug+rwx qatrack/media
    chmod a+rw logs/{migrate,debug}.log

Since we are now using a different Python virtual environment we need to update
the `WSGIPythonHome` variable.  Open your Apache config file (either
/etc/apach2/sites-available/qatrack.conf  or
/etc/apache2/sites-available/default.conf or /etc/apache2/httpd.conf) and set
the virtualenv path correctly:

.. code-block:: apache

    WSGIPythonHome /home/YOURUSERNAME/venvs/qatrack3

    # or for daemon mode

    WSGIDaemonProcess qatrackplus python-home=/home/YOURUSERNAMEHERE/venvs/qatrack3 python-path=/home/YOURUSERNAMEHERE/web/qatrackplus

and then restart Apache:

.. code-block:: console

    sudo service apache2 restart


Last Word
~~~~~~~~~

There are a lot of steps getting everything set up so don't be discouraged if
everything doesn't go completely smoothly! If you run into trouble, please get
in touch on the :mailinglist:`mailing list <>`.

Appendix 1: Hosting QATrack+ at a non-root URL
----------------------------------------------

If you want to host QATrack+ somewhere other than the root of your server (e.g.
you want to host the QATrack+ application at http://myserver/qatrackplus/), you
will need to ensure mod_rewrite is enabled:

.. code-block:: console

    sudo a2enmod rewrite
    sudo service apache2 restart

and you will need to include the following lines in your qatrack/local_settings.py file

.. code-block:: python

    FORCE_SCRIPT_NAME = "/qatrackplus"
    LOGIN_EXEMPT_URLS = [r"^qatrackplus/accounts/", r"qatrackplus/api/*"]
    LOGIN_REDIRECT_URL = "/qatrackplus/qa/unit/"
    LOGIN_URL = "/qatrackplus/accounts/login/"

and edit `/etc/apache/sites-available/qatrack.conf` so that the WSGIScriptAlias
is set correctly:

.. code-block:: apache

    WSGIScriptAlias /qatrackplus /home/YOURUSERNAMEHERE/web/qatrackplus/qatrack/wsgi.py

