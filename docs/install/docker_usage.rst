Usage Tips
==========

Running the Services
--------------------

.. code-block:: console

    $ docker compose up

Single press `CTRL-C` to stop gracefully.


Running the Services in the Background and Automatic Start
----------------------------------------------------------

To have QATrack+ and the other services start on boot, add the `-d` flag to the
up command to detach the process:

.. code-block:: console

    $ docker compose up -d


Viewing the Running Containers
------------------------------

.. code-block:: console

    $ docker compose ps

This will print information on the running containers, such as their health state, 
exposed ports, uptime and what image they are using.


Viewing the Container Logs
--------------------------

To view full container logs, call:

.. code-block:: console

    $ docker compose logs

To view the last 100 entries, you can use:

.. code-block:: console

    $ docker compose logs -n 100

To view the last 100 entries and follow the logs live in the terminal, call:

.. code-block:: console

    $ docker compose logs -n 100 -f


Press `CTRL-C` to stop.


Backup Up Media Files and Database
----------------------------------

To perform an immediate one-off backup, run:

.. code-block:: console

    $ docker compose run --rm --no-deps backup backup

``docker compose run --rm --no-deps backup`` runs an ephemeral backup service
container that shares the same volumes as the running container create when
``docker compose up`` is used.

Do the services need stopping first?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**No, and the scheduled backup cannot do it anyway** - the ``backup`` container
runs its own cron inside the stack and has no way to stop the other services.
Every nightly backup is therefore taken on a running system, by design.

That is safe for the database on its own. ``pg_dump`` takes a transactionally
consistent snapshot, so the dump is never a half-written database no matter what
is happening at the time.

**What stopping the writers buys is a database and a media archive from the same
moment**, and it is worth being precise about how much that is worth here. The
script dumps the database and *then* archives the media files, so there is a
window between the two. A file uploaded in that window ends up in the archive
with no database row pointing at it, which is harmless - and the reverse case,
a referenced file missing from the archive, cannot arise from anything QATrack+
does: nothing in it deletes an upload, and a corrected upload is stored beside
the file it replaces rather than over it. See :ref:`qatrack_backup`.

So on a correctly run system the hot backup is not losing anything; what the
pause gives you is a pair you can reason about without that argument, which is
worth having before an upgrade and worth having if your site's practice expects
it. Take it the same way you would restore one:

.. code-block:: console

    $ docker compose stop django django-q
    $ docker compose run --rm --no-deps backup backup
    $ docker compose up -d django django-q

``postgres`` and ``backup`` stay up; it is only the two services that write that
need to be out of the way. Out of clinical hours the downtime is a minute or two,
and nothing about the scheduled nightly backup has to change.


Listing the Backup Files in the Backups Storage
-----------------------------------------------

Use the following command to list backup files in order of oldest to most recent
at the bottom.

.. code-block:: console

    $ docker compose exec backup ls -lhtr /backups


Restoring Media Files
---------------------

.. code-block:: console

    $ docker compose run --rm --no-deps backup restore-media <media_XXXXXXXX_XXXXXX.tar.gz>


Restoring the Database
----------------------

**Stop everything that can write to the database first.** Restoring is not the
mirror image of backing up: taking a backup is safe on a running system, and
replacing the database is not.

.. code-block:: console

    $ docker compose stop django django-q
    $ docker compose run --rm --no-deps backup restore-db <db_XXXXXXXX_XXXXXX.dump>
    $ docker compose up -d django django-q

``restore-db`` asks you to type the database name before it does anything, and
it says the same thing there. It will not refuse to run with the services up,
though - it drops the database with ``--force``, which **terminates their
connections** rather than waiting for them. So on a live system a restore
interrupts whatever anybody was submitting at that moment, and leaves the task
cluster free to write into a database that is part-way through being replaced.
Neither failure announces itself.

.. note::

    **Backups do not need this.** The backup script is written so that a backup
    can be taken safely while the system is running, which is what lets the
    ``backup`` container keep to its own schedule without anybody coordinating
    with it.


Restarting the Service Containers
---------------------------------

To restart the services, keeping the existing containers, run:

.. code-block:: console

    $ docker compose restart


Shutdown the Service Containers
-------------------------------

To shutdown the services, keeping the existing containers, run:

.. code-block:: console

    $ docker compose stop


Shutdown the Services, Remove the Containers and Docker Volumes
---------------------------------------------------------------

.. warning::

  If you store your database data in a docker volume, *this will delete
  your database*. The next time you start the containers, a fresh empty database
  will be created.

.. warning::

  If you store your backups in a docker volume, *this will delete your backups*.

.. warning::

  If you store your secret key in ``secret_key.txt`` in the user-data docker volume,
  *this will delete your secret key file*.

To shutdown the server, remove the containers and the docker volumes, run:

.. warning::

    **IRREVERSIBLE, erases volumes**

.. code-block:: console

    $ docker compose down -v

If for some reason you need to, the following commands will delete all docker
data from the current project, including the built images:

.. warning::

    **IRREVERSIBLE, erases volumes**

.. code-block:: console

    $ docker compose down -v --rmi all


Accessing the Linux Shell on the Running Containers
---------------------------------------------------

You can log into the shell on running containers. This can be useful to debug
various issues, such as bind mounts write permissions, or to inspect the
files or directories on the container.

.. note::

  Once logged into the container shell, use the ``exit`` command to exit.

**django container** which serves the QATrack+ app:

.. code-block:: console

    $ docker compose exec django bash

In particular, to inspect the installed python packages in QATrack's virtual
environment, you can use:

.. code-block:: console

    $ docker compose exec django bash
    user@qat-django:/app$: pip list

**django-q container** which runs QATrack+ background tasks:

.. code-block:: console

    $ docker compose exec django-q bash

**backups container** which runs periodic backups:

.. code-block:: console

    $ docker compose exec backup sh

**nginx container** which runs the NGINX as reverse proxy:

.. code-block:: console

    $ docker compose exec nginx sh


Running Django Management Commands
----------------------------------

If you need to run any Django management commands, you may do so by calling:

.. code-block:: console

    $ docker compose exec django python manage.py [options] args


This requires that the django container is already running.

Accessing the Django Shell
~~~~~~~~~~~~~~~~~~~~~~~~~~

In particular, if you need to access the Django shell run the following:

.. code-block:: console

    $ docker compose exec django python manage.py shell



Updating QATrack+
-----------------

This text presents general instructions to give a broad overview of the upgrade process.

#. Review the release notes.
#. Check if any version-specific upgrade instructions are listed in
   :doc:`Installation and Deployment Options <./install>`.
#. Make sure you have a fresh backup of your DB that you can restore successfully.

To update the application from Github run:

.. code-block:: console

    $ docker compose stop
    $ git pull
    $ git checkout v.4.x.x  # checkout the Git tag matching the version you want

.. note::

  QATrack+ versions each correspond to a tag in the
  `QATrack+ repository on Github <https://github.com/qatrackplus>`_.


Once any files have changed in the qatrackplus directory you need to run the following:

.. code-block:: console

    $ docker compose build
    $ docker compose up  # or docker compose up -d


``docker compose up`` will then detect that newer versions of the images are available
and use them to recreate the containers.

At startup, the django container will:
  #. Attempt to create a cache table in the DB (a no-op if it already exists)
  #. Runs pending migrations if any exist. This is where the tables of the DB are
     migrated when upgrading to a newer version. It may take some time to run.
     Once migrations are finished, your DB is upgraded to the version you chose.
  #. Collect static files. If the new version requires any different static files,
     these will be copied to the static volume.
