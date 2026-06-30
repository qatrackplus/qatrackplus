.. _win_upgrading_40:

Upgrading an existing Windows v3.1 installation to v4.0.0
===========================================================

This guide will walk you through upgrading your existing v3.1 installation to
v4.0.0. If you currently have an older version of QATrack+, please reach out to the QATrack+ team for assistance with upgrading to v3.1 first.


.. contents::
    :local:
    :depth: 2


Introductory Notes
~~~~~~~~~~~~~~~~~~~

There are significant changes to the tooling and dependencies in v4.0.0, so please read through this entire guide before attempting to upgrade.  If you have any questions or concerns, please reach out to the QATrack+ team for assistance. Some of these changes include: 

- The Python virtual environment is now managed by the `uv` package manager, which will handle a lot of the python heavy lifting for you.  
    - The old `venvs/qatrack31` directory is no longer needed. 
    - Manual installations of Python and pip are no longer required. 
- We are going away from including specific versions in file names for the CherryPy service and scheduled task.  The new service is called `QATrack+ CherryPy Service` and the scheduled task is called `QATrack+ Django Q Cluster`.  This will make it easier to apply future patches.


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

Backing up your Media folder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is also crucial to back up your uploaded media files before upgrading. Navigate to your QATrack+ installation directory (e.g., ``C:\deploy\qatrackplus\qatrack\media``) and create a copy or zip archive of the entire ``media`` folder. Save this backup in a safe location.

Backing up your local_settings.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your configuration, including database credentials and site-specific settings, is stored in ``local_settings.py``. Navigate to ``C:\deploy\qatrackplus\qatrack\`` and create a backup copy of ``local_settings.py`` before proceeding with the upgrade.

Stopping Background Services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before changing branches or creating a new environment, you must stop your background task runner to prevent tasks from executing during the upgrade. You must also stop and remove the old CherryPy service using your existing Python environment. Open a PowerShell window and run:

.. code-block:: powershell

    # Stop background task runner
    # Note: Replace "QATrack+ Django Q Cluster" if you used a different name for your scheduled task
    >>  Stop-ScheduledTask -TaskName "QATrack+ Django Q Cluster"
    # Stop and remove CherryPy service
    >>  cd C:\deploy
    >>  .\venvs\qatrack31\Scripts\Activate.ps1
    >>  cd qatrackplus
    >>  python QATrack31CherryPyService.py stop
    >>  python QATrack31CherryPyService.py remove


To verify that the service has been removed, please open the **Services** application and check that there are no entries with QATrack or CherryPy in the name. If the service is still present, then open a CMD window (not PowerShell) as Administrator and run the following command to remove it:

.. code-block:: console

    >>  sc delete "QATrack+ CherryPy Service"





Checking out version 4.0.0
~~~~~~~~~~~~~~~~~~~~~~~~~~

First we must check out the code for version 4.0.0 in a PowerShell window:

.. code-block:: powershell

    >>  cd C:\deploy\qatrackplus
    >>  git fetch origin
    >>  git checkout releases/4.0

.. dropdown:: Tag

    If you prefer to use a tag instead of a branch, you can check out the `v4.0.0` tag instead. We are switching defaults away from tags to branches for ease of patch distribution. Future patches can be applied simply with a git pull command, whereas tags are immutable and cannot be updated. To check out the tag, run the following commands in a PowerShell window:

    .. code-block:: powershell

        >>  cd C:\deploy\qatrackplus
        >>  git fetch origin
        >>  git checkout v4.0.0


Updating our Python environment
-------------------------------

For version 4.0.0, QATrack+ now uses the `uv` package manager, which will handle a lot of the python heavy lifting for you. We will create a new virtual environment inside the `qatrackplus` directory. Your old `venvs/qatrack31` directory is no longer needed.

First, delete the old virtual environment, and uninstall all installed python instances. Then we will install `uv` from the executable and create a new virtual environment. We will use powershell to fetch the installer. If you'd like you can download the latest `uv` installer from the [uv releases page](https://github.com/astral-sh/uv/releases).

First, install `uv` and create the new environment:

.. code-block:: powershell

    >>  cd C:\deploy
    >>  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    >>  cd qatrackplus
    >>  uv env create .venv
    >>  uv sync --extras win --extras mssql 
    
Next, activate your new virtual environment:

.. code-block:: powershell

    >>  .\.venv\Scripts\Activate.ps1

Your command prompt should now be prefixed with `(qatrackplus)` or `(.venv)`.


Performing the migration
------------------------

We can now migrate the tables in our database:

.. code-block:: powershell

    >>  python manage.py migrate

and then we need to update all our static media files:

.. code-block:: powershell

    >>  python manage.py collectstatic


Updating and Restarting Windows Services
----------------------------------------

Because the Python executable path has changed with the move to `uv`, you must install the new CherryPy service using the new environment. 

.. code-block:: powershell

    >>  cp deploy\win\QATrackCherryPyService.py .
    >>  python QATrackCherryPyService.py --startup=auto install
    >>  python QATrackCherryPyService.py start

You must also update the Windows Task Scheduler. Open the **Task Scheduler** application, find the **QATrack+ Django Q Cluster** task, and edit the **Action** to run the new Python executable located at: `C:\deploy\qatrackplus\.venv\Scripts\python.exe`.

Finally, restart the scheduled task:

.. code-block:: powershell

    >>  Start-ScheduledTask -TaskName "QATrack+ Django Q Cluster"
