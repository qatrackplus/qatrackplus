.. _linux_upgrading_31:


Upgrading an existing Linux v3.X.Y installation to v3.1.1.2
===========================================================

.. note::

    This guide assumes you have at least a basic level of familiarity with
    Linux and the command line.


This guide will walk you through upgrading your existing v3.X.Y installation to
v3.1.1.2.  If you currently have a 0.3.x version of QATrack+, you first need to
follow the :ref:`instructions to upgrade to 3.1 <linux_upgrading_030_to_31>`,
before carrying out these instructions.

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


Make sure your existing packages are up to date
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo apt update
    sudo apt upgrade


Check out version 3.1.1.2
-------------------------

We can now grab the latest version of QATrack+.  To checkout the code enter the
following commands:

.. code-block:: bash

    cd ~/web/qatrackplus
    git fetch origin
    git checkout v3.1.1.2


Updating our Python environment
-------------------------------

Activate your virtual environment:

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


Performing the migration
------------------------

We can now migrate the tables in our database:

.. code-block:: console

    python manage.py migrate


and then we need to collect all our static media files:

.. code-block:: bash

    python manage.py collectstatic

Restart QATrack+
----------------

Finally we need to restart QATrack+

.. code-block:: console

    sudo service apache2 restart
    sudo supervisorctl reread
    sudo supervisorctl update


You should now be able to log into your server at http://yourserver/!
