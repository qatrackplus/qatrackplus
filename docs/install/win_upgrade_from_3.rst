.. _win_upgrading_31:

Upgrading an existing Windows v3.X.Y installation to v3.1.1.3
=============================================================

This guide will walk you through upgrading your existing v3.X.Y installation to
v3.1.1.3.  If you currently have a 0.3.x version of QATrack+, you first need to
follow the :ref:`instructions to upgrade to 3.1 <win_upgrading_030_to_31>`,
before carrying out these instructions.


.. contents::
    :local:
    :depth: 2


Take a snapshot
~~~~~~~~~~~~~~~

If your QATrack+ server exists on a virtual machine, now would be a great time
to take a snapshot of your VM in case you need to restore it later!  Consult
with your IT department on how to do this.


Backing up your database
~~~~~~~~~~~~~~~~~~~~~~~~

It is important you back up your database before attempting to
upgrade.  In order to generate a backup open SQL Server Management Studio
(SSMS), right click on your database then select `Tasks -> Back Up..`

.. figure:: images/win/backup_menu.png
    :alt: Backup Menu Item

    Backup Menu Item

Select `Copy-only backup` and make sure the `Backup component` is set to
`Database`. Take note of where the backup is being stored and then click `OK`:


.. figure:: images/win/backup_dialog.png
    :alt: Backup Dialog

    Backup Dialog


Checking out version 3.1.1.3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First we must check out the code for version 3.1.1.3 in a PowerShell window:

.. code-block:: console

    cd C:\deploy\qatrackplus
    git fetch origin
    git checkout v3.1.1.3


Updating our Python environment
-------------------------------

Activate your virtual environment:

.. code-block:: bash

    
    cd C:\deploy
    .\venvs\qatrack31\Scripts\Activate.ps1

Your command prompt should now be prefixed with `(qatrack31)`.

It's also a good idea to upgrade `pip` the Python package installer:

.. code-block:: bash

    pip install --upgrade pip

We will now install all the libraries required for QATrack+ (be patient, this
can take a few minutes!):

.. code-block:: bash

    cd C:\deploy\qatrackplus
    pip install -r requirements\win.txt


Performing the migration
------------------------

We can now migrate the tables in our database:

.. code-block:: console

    python manage.py migrate

and then we need to update all our static media files:

.. code-block:: bash

    python manage.py collectstatic


Restart QATrack+
----------------

Finally we need to restart QATrack+

.. code-block:: bash

    python manage.py QATrack31CherryPyService.py restart
    Stop-ScheduledTask -TaskName "QATrack+ Django Q Cluster"
    Start-ScheduledTask -TaskName "QATrack+ Django Q Cluster"
