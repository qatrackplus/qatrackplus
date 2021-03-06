.. _qatrack_backup:

Backing up QATrack+
===================

.. note::

    Note, please speak with your server administrator to see if you already
    have a backup plan in place for both databases and files. If you already do
    then great, you can ignore this page! If not then please read on.


It is **highly** recommended you put an automated backup solution in place for
your QATrack+ installation. It is also highly recommended that your backups not
reside on the QATrack+ server itself. That is to say, you should favour having
your backups stored on a remote system (e.g. a network or shared drive) so that
if your server loses its primary hard drive you will still have access to your
backups.  Example backup scripts for Linux (to be run by cronjob) and Windows
(run by Task Scheduler) are included below. These scripts back up nightly, and
retain daily backups for a week, weekly backups for 5 weeks and monthly backups
for ~1 year (these values are configurable).

.. danger::

    The scripts included below can be used as is, or modified to suit your
    needs, but ultimately **it is up to you to ensure your QATrack+
    installation is backed up correctly**.


Backing up QATrack+ on Linux
----------------------------

To use one of the example backup scripts on a Linux install, copy the
appropriate script for your database to the main QATrack+ directory:

.. code-block:: console

    cp deploy/postgres/backup.sh .
    # - or - #
    cp deploy/mysql/backup.sh

Now edit the backup.sh file and set the various options in the configuration
section. Add the `backup.sh` script to your crontab:

.. code-block:: console

    # make the script executable by everyone so cron can run it
    chmod 755 backup.sh

    # add the crontab entry to run every night at 3am
    (crontab -l && echo "0 3 * * * $PWD/backup.sh") | crontab -

    # -or edit your crontab manually and append a line like "0 3 * * * /home/randlet/web/qatrackplus/backup.sh"
    crontab -e


Backing up QATrack+ on Windows
------------------------------

First copy the script `deploy/backup/win/backup.ps1` to the main qatrackplus
directory:

.. code-block:: console

    cd C:\deploy\qatrackplus
    cp deploy\win\backup.ps1 .

Then edit the backup.ps1 file and set the configuration variables appropriately.


Next open the Task Scheduler and select `Create Task` in the `Action` menu.

On the `General` tab set the `Name` field to `QATrack+ Backup` (or similar).
Check the `Run whether user is logged on or not` checkbox.


On the `Triggers` tab click `New` and select `Daily` and choose the `Start`
date and `Time` (e.g. 3am) and `Recur every` to `1` then click OK.

Now go to the `Actions` tab and click `New` then enter `PowerShell.exe` in the
`Program/Script` field and `-ExecutionPolicy Bypass
C:\\deploy\\qatrackplus\\backup.ps1` in the `Add Arguments` field.

Now save your scheduled task and run it and manually to confirm it worked
correctly.


Using Django to Dump The Database To JSON
-----------------------------------------

In some cases you may want to move your database from one type of SQL database
to another, say from Postgres to SQLite.  In this case, one way to do this is
to dump your database to a JSON file and then load it in your other database.

Dumping your database
.....................

Open a terminal, and activate your virtual environment and then:


.. code-block:: console

    python manage.py dumpdata > qatrack-dump.json


The qatrack-dump.json file can now be used to populate a fresh database.


Loading your database
.....................


.. danger::

    This will completely erase all of the data in your database.  Only do this
    if you are sure you are dealing with a fresh database


You must load your previously dumped database into the same version of
QATrack+.  First you need to create a new database, and then configure QATrack+
to access it. Then migrate your database and clean out the autopopulated data:

.. code-block:: console

    python manage.py migrate
    python manage.py shell -c "from qatrack.qa.models import *; TestListInstance.objects.all().delete(); UnitTestCollection.objects.all().delete(); ContentType.objects.all().delete()"


Then you can load in your new data:


.. code-block:: console

    python manage.py loaddata qatrack-dump.json




