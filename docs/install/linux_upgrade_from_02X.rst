.. _linux_upgrading_02X_to_31:


Upgrading an existing Linux v0.2.X installation to v3.1.1
=========================================================


.. note::

    This guide assumes you have at least a basic level of familiarity with
    Linux and the command line.


This document will walk you through migrating an existing v0.2.X version of
QATrack+ to a new Ubuntu 18.04 or Ubuntu 20.04 server.  Although it may be
possible, upgrading an Ubuntu 14.04 or Ubuntu 16.04 installation in place is
not recommended. This guide assumes you are moving to a new server.  If you
need advice please get in touch on the :mailinglist:`mailing list <>`.


On your old server
------------------

The first step to migrating your existing QATrack+ installation is to generate
the backup files to move everything to your new server.

Backup your QATrack+ install data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The process to generate and restore a database dump may vary depending on how
you have things configured, your operating system version, or the version of
database software you are using.  The steps below can be used as a guide,
but they may need to be tweaked for your particular installation.

.. note::

    We will assume you are currently using a database named 'qatrackplus' but
    if not (check the DATABASE settings in qatrack/local_settings.py) replace
    'qatrackplus' in the instructions below with your database name (e.g.
    qatrackdb).


.. code-block:: bash

    # postgres
    sudo -u postgres pg_dump -d qatrackplus > backup-0.2.X.sql 

    # or for MySQL
    mysqldump --user qatrack --password=qatrackpass qatrackplus > backup-0.2.X.sql 


and create an archive of your uploads directory:

.. code-block:: bash

    tar czf qatrack-uploads.tgz qatrack/media/uploads/


On your new server
------------------

Copy the backup-0.2.X.sql and qatrack-uploads.tgz to your new server, these
will be needed below.


Prerequisites
-------------

Make sure your existing packages are up to date:

.. code-block:: bash

    sudo apt update
    sudo apt upgrade

You will need to have the `make` command and a few other packages available for
this deployment. Install install them as follows:

.. code-block:: bash

    sudo apt install make build-essential python-dev python3-dev python3-tk python3-venv


Installing a Database System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you were using Postgres before, then install it again. Likewise, if your
previous server was using a MySQL database, then install MySQL/MariaDB

Installing PostgreSQL (Only required if you were previously using Postgres)
...........................................................................

If you do not have an existing database server, you will need to install
PostgreSQL locally. Run the following commands:

.. code-block:: console

    sudo apt-get install postgresql libpq-dev postgresql-client postgresql-client-common


Now edit /etc/postgresql/12/main/pg_hba.conf (use your favourite editor, e.g.
`sudo nano /etc/postgresql/12/main/pg_hba.conf` (note, if you have a different
version of Postgres installed, then you would need to change the 12 in that
path e.g. /etc/postgresql/9.3/main/pg_hba.conf) and scroll down to the bottom
and change the instances of `peer` to `md5` so it looks like:

.. code-block:: console


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

.. code-block:: console

    sudo service postgresql restart


Installing MySQL (Only required if you were previously using MySQL)
...........................................................................

.. code-block:: bash

    sudo apt-get install mysql-server libmysqlclient-dev


Restoring your previous database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We can now restore your previous database:

.. code-block:: bash

    sudo -u postgres psql -c "CREATE DATABASE qatrackplus;"
    sudo -u postgres psql -d qatrackplus < backup-0.2.X.sql
    sudo -u postgres psql -c "CREATE USER qatrack with PASSWORD 'qatrackpass';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE qatrackplus to qatrack;"

    # or for MySQL (omit the -p if your mysql installation doesn't require a password for root)
    sudo mysql -p -e "CREATE DATABASE qatrackplus;"
    sudo mysql -p --database=qatrackplus < backup-0.2.X.sql
    sudo mysql -p -e "GRANT ALL ON qatrackplus.* TO 'qatrack'@'localhost';"


Now confirm your restore worked:

.. code-block:: bash

    # postgres: Should show Count=1234 or similar
    PGPASSWORD=qatrackpass psql -U qatrack -d qatrackplus -c "SELECT COUNT(*) from qa_testlistinstance;"

    # mysql: Should show Count=1234 or similar
    sudo mysql --password=qatrackpass --database qatrackplus -e "SELECT COUNT(*) from qa_testlistinstance;"


Assuming your database restoration was successful, you may now proceed with
upgrading the database to v0.3.0.


Installing and configuring Git and checking out the QATrack+ Source Code
------------------------------------------------------------------------

Ensure you have git installed with the following command:

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
    git checkout v0.2.9.2


Restore your upload files
.........................

Assuming you are on a new server and  have an uploads file that you want to
restore you should do so now:

.. code-block:: bash

    # assuming your qatrack-uploads.tgz is in your home directory

    cd ~/web/qatrackplus
    mv ~/qatrack-uploads.tgz .
    sudo tar xzf qatrack-uploads.tgz


Use your favourite text editor to create a local_settings.py file in
`~/web/qatrackplus/qatrack/` with the following contents:


.. code-block:: python

    # for postgres
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'qatrackplus',
            'USER': 'qatrack',
            'PASSWORD': 'qatrackpass',
            'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',  # Set to empty string for default. Not used with sqlite3.
        },
    }

    # or for mysql
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'qatrackplus',
            'USER': 'qatrack',
            'PASSWORD': 'qatrackpass',
            'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',  # Set to empty string for default. Not used with sqlite3.
        },
    }


Setting up our Python environment (including virtualenv)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have a v0.2.9 database, you will only need a Python 3 installation,
however if you have an older QATrack+ installation, you will also require
Python 2.7. If you have a v0.2.9 database, you can skip this next section.

Migrating 0.2.X (where X < 9) to v0.2.9
.......................................

First install virtualenv, then create and activate a new Python 2 environment:

.. code-block:: bash

    cd ~/web/qatrackplus
    sudo apt install python-virtualenv
    mkdir -p ~/venvs
    virtualenv -p python2 ~/venvs/qatrack2
    source ~/venvs/qatrack2/bin/activate
    pip install --upgrade pip

Now install the required Python packages:

.. code-block:: bash

    pip install -r requirements/base.txt
    # for postgres
    pip install psycopg2-binary
    # for mysql
    pip install mysqlclient


Now migrate your database to v0.2.9

.. code-block:: bash

    python manage.py syncdb
    python manage.py migrate

and deactivate the virtualenv

.. code-block:: bash

    deactivate

Migrating 0.2.9 to 0.3.0
------------------------

Check out QATrack+ version 0.3.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to upgrade our 0.2.9 installation to 0.3.0, first we need to checkout
the QATrack+ v0.3.0 source code:

.. code-block:: bash

    cd ~/web/qatrackplus
    git checkout v0.3.0.19


Creating our virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create and activate a new Python 3 virtual environment:

.. code-block:: console

    mkdir -p ~/venvs
    python3 -m venv ~/venvs/qatrack3
    source ~/venvs/qatrack3/bin/activate
    pip install --upgrade pip

We will now install all the libraries required for QATrack+ with PostgresSQL
(be patient, this can take a few minutes!):

.. code-block:: console

    # for postgres
    pip install -r requirements/postgres.txt

    # or for MySQL:
    pip install -r requirements/mysql.txt


Migrating the 0.2.9 database to 0.3.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We are now ready to migrate our 0.2.9 database to v0.3.0:

.. code-block:: console

    python manage.py migrate --fake-initial


Installing Apache web server and mod_wsgi
-----------------------------------------

The next step to take is to install and configure the Apache web server.
Apache and mod_wsgi can be installed with the following commands:

.. code-block:: bash

    sudo apt-get install apache2 apache2-dev libapache2-mod-wsgi-py3 python3-dev


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


Next Steps
----------

Now that you have upgraded to 0.3.0, you should proceed directly to
:ref:`upgrading to v3.1.1 from v0.3.0 <linux_upgrading_030_to_31>`;
