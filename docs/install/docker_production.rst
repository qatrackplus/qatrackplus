Running in Production
---------------------

The ``.env.example`` file provides a valid safe configuration for production.

Once copied to ``.env``, you can run the default setup it by calling:

.. code-block:: console

    $ docker compose up --build

, which will build the images and bring the services up. Hit ``CTRL+C`` to exit.

However, most users will want to run with customized options.

For guidance on the various available settings, refer to the previous section
:doc:`Docker Deployment Configuration <./docker_config>`, as well as
:doc:`Configuring a QATrack+ Installation <./config>`.

The main characteristics of the default production setup are:
  * Strict hostname matching to what is set in ``ALLOWED_HOSTS``. Since ``ALLOWED_HOSTS``
    defaults to ``qatrackplus.domain``, **you will not be able to connect unless you use this
    hostname or change** ``ALLOWED_HOSTS``.
  * Gunicorn used to serve the QATrack+ app, behind NGINX as reverse proxy.
  * ``HTTP_OR_HTTPS`` set to ``http`` and HTTP served on port 80 by NGINX.
  * NGINX serves static files.
  * Docker named volumes used for persistent storage of DB, backups, media files and ``secret_key.txt``.
  * PostgreSQL published on ``127.0.0.1:5434`` on the host.


Customizing ``.env.example`` for Production
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Named Volumes vs Bind Mounts
............................

Decide on whether to use Docker named volumes (the default), or bind mounts.
If you want to use a bind mount, set one of the variables in the
``Docker bind mounts`` section.

Docker named volumes reside on the disk of your host. If the disk is running low on
space because the database and media files are growing, then you may have to resize
the disk.

Bind mounts allow you to use remote storage such as a SAN to persist data.

Whichever you choose, ensure that regular backups are done to a safe location.

For example, a configuration with the PostgreSQL DB residing on a Docker named
volume on the host's disk and a bind mount to a remote SAN storage for backups is a
reasonable choice.


Set the PostgreSQL Credentials and DB Name
..........................................

Change the values of ``POSTGRES_USER``, ``POSTGRES_PASSWORD`` and ``POSTGRES_DB``
to your liking.


Set ``ALLOWED_HOSTS``
.....................

Set ``ALLOWED_HOSTS`` to a comma-separated string of valid hostnames or IP
addresses that will be used to connect to QATrack+, e.g. ``qatrackplus.domain``
if you only want to allow connections that use ``http(s)://qatrackplus.domain``.


Set ``SECRET_KEY`` (Recommended, Optional)
..........................................

Set ``SECRET_KEY`` to a secret unique value, and write it to a safe location for
future use.

If you do not set ``SECRET_KEY``, the system will generate a safe value for you
in the ``secret_key.txt`` file in the user-data volume. You must then access the
user-data storage to backup its value to safe storage for future use.

.. warning::

    **Treat that file as a backup item in its own right.** If it is lost - a
    deleted volume, a restore that misses it - the next start generates a new
    key, and QATrack+ comes up looking perfectly healthy. What has actually
    happened, measured on 2026-10-18, is that every signed-in user is signed
    out, every outstanding password-reset link stops working, and the only
    trace in the log is a ``Session data corrupted`` line for each affected
    session, which says nothing about the cause. Start-up now prints a
    ``SECRET_KEY:`` notice when it generates a key, so this is visible in
    ``docker compose logs django`` if you are looking.

    Setting ``SECRET_KEY`` in ``.env`` avoids the whole question: the file is
    then never used.


Enable HTTPS/SSL (Optional)
...........................

1. Define ``SSL_DIR``, ``NGINX_SSL_CERTIFICATE_FILE`` and
   ``NGINX_SSL_CERTIFICATE_KEY_FILE``.
2. Make sure the required SSL certificate file and SSL certificate key files are
   located in ``SSL_DIR`` on your host.
3. Set ``HTTP_OR_HTTPS`` to ``https``.


Customize Django and QATrack+ settings (Optional)
.................................................

Finish customizing your ``.env`` file by uncommenting and changing any Django or QATrack+
settings you need.

Refer to the previous section :doc:`Docker Deployment Configuration <./docker_config>`
and to :doc:`Configuring a QATrack+ Installation <./config>` for guidance.


Build the Production Images
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once your ``.env`` is customized to your liking, build the images:

.. code-block:: console

    $ docker compose build


Run the Containers in Detached Mode
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Running the containers in detached mode allows you to run the services in the
background, letting you regain control of the terminal after launching the
command.

This command will also ensure the services are brought back up automatically in case the
host is rebooted.

.. code-block:: console

    $ docker compose up -d


.. _docker_first_user:

Create Your First User
^^^^^^^^^^^^^^^^^^^^^^

No user account is created for you, so create one before your first login.
The ``django`` service runs the application, so run ``createsuperuser`` there
and answer its prompts:

.. code-block:: console

    $ docker compose exec django python manage.py createsuperuser

You can then sign in with the credentials you just chose.

.. note::

    This can be done for you instead: set ``DJANGO_SUPERUSER_USERNAME``,
    ``DJANGO_SUPERUSER_PASSWORD`` and ``DJANGO_SUPERUSER_EMAIL`` in ``.env``
    before the first start and the entrypoint creates the account. Remove them
    once it exists - a password in ``.env`` is a password on disk in plain text.
    See the Docker configuration page for the full list.
