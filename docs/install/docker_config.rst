Docker Deployment Configuration
===============================

This section is meant to explain in general how the Docker deployment can be
configured. Specific instructions on running in production mode or development
mode are presented in the following sections.

Configuring QATrack+ when deployed under Docker is possible by setting environment
variables. The values of the variables are set from the ``.env`` file, which you
must create, as it is not stored in the repository.

From the ``deploy/docker/`` directory, copy ``.env.example`` to ``.env``. This step is
applicable to both production and development setups.

.. code-block:: console

    $ cp .env.example .env

.. note::

    ``.env`` and ``.env.example`` are both *hidden* files. To list them in the
    terminal, you must use the ``-a`` flag of ``ls``, e.g. use ``ls -la``.

The ``.env.example`` is self-documenting and provides sane defaults for running
QATrack+ in production.


Django and QATrack+ Settings
----------------------------

Most, but not all, of QATrack+ settings are available in the form of environment
variables. Similarly, a few useful Django settings can be passed as environment
variables.

.. note::

  Since the settings in Django/QATrack+ are python variables, environment variable
  values must be encoded in such a way that they will translate to valid python values.

  ===================  =================================  ===============  ============================================================================
  Python Type          Python Example                     Env Var Type     Env Var Example
  ===================  =================================  ===============  ============================================================================
  ``str``              ``'admin@domain'``                 text             ``admin@domain``
  ``int``              ``25``                             integer          ``25``
  ``float``            ``2.5``                            number           ``2.5``
  ``bool`` (true)      ``True``                           multiple choice  one of ``1``, ``true``, ``yes``, ``on`` in upper/lower case or CamelCase
  ``bool`` (false)     ``False``                          multiple choice  one of ``0``, ``false``, ``no``, ``off`` in upper/lower case or CamelCase
  ``list[str]``        ``['foo', 'bar']``                 CSV text         ``foo,bar``
  ``list[list[str]]``  ``[['Admin', 'admin@domain']]``    JSON text        ``[["Admin", "admin@domain"]]``
  ``dict``             ``{'foo': 1, 'bar': 2}``           JSON text        ``{"foo": 1, "bar": 2}``
  ===================  =================================  ===============  ============================================================================

For the list of supported environment variables, consult ``.env.example``.

The purpose of the environment variables listed in ``.env.example`` is often
self-explanatory. For more information of the QATrack and Django settings,
refer to :doc:`Configuring a QATrack+ Installation <./config>`.


Notable Django or QATrack+ Settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ALLOWED_HOSTS (required)
  The only mandatory Django setting when running in production. Set this to the
  hostname and/or IP address used when connecting to QATrack+. Defaults to
  ``qatrackplus.domain``. If your goal is only to run QATrack+ locally for
  development, you can leave this at its default value, as ``localhost`` and
  ``127.0.0.1`` are automatically injected into ``ALLOWED_HOST`` when running
  in development mode.

DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_EMAIL (optional)
  Set all three and the django container creates that superuser on start-up, so a
  new deployment can be signed into without running :ref:`createsuperuser
  <docker_first_user>` by hand. Set none of them - the default - and the
  entrypoint skips the step entirely.

  Django's ``createsuperuser --noinput`` requires the username; it is the
  variable the entrypoint tests for. The account is created once and nothing
  touches it afterwards, so changing the password here later has no effect:
  change it in QATrack+, and remove the variables once the account exists, since
  a password in ``.env`` is a password on disk in plain text.

SECRET_KEY (optional)
  The Django secret key. It's recommended you set this to a unique value which
  will be backed up in secure storage. If this variable is unset, the system will
  generate ``secret_key.txt`` in the user-data storage (either a Docker volume or a
  bind mount).


AD_CLEAN_USERNAME (optional)
  QATrack+ supports the ``AD_CLEAN_USERNAME`` setting, which a user may set to
  a callable to clean the user names coming from Active Directory. Since defining
  a callable with an environment variable is not possible, the ``AD_USERNAME_CLEANING``
  variable is provided instead to use common user name cleaning strategies. Refer to
  ``.env.example`` for more details if you need to clean AD user names.


Other Docker Deployment Settings
--------------------------------

This section will briefly explain the possible customizations to the Docker
deployment.


Docker Bind Mounts
^^^^^^^^^^^^^^^^^^

By default, persistent storage for media, backups and ``secret_key.txt`` will use Docker
named volumes. If you want, you can change this behavior by switching to bind mounts,
which will mount a directory on your host to a directory in the service container.
To do this, set any or all of the following variables:

MEDIA_DIR (optional)
  Set this to the path of a directory on your host to use a bind mount for media files.

BACKUPS_DIR (optional)
  Set this to the path of a directory on your host to use a bind mount for backup files.

USER_DATA_DIR (optional)
  Set this to the path of a directory on your host to use a bind mount for storing
  ``secret_key.txt``, This is only relevant if you have not already set the ``SECRET_KEY``
  variable.


Docker Build Settings (Advanced)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

  These settings can be safely ignored and left to their default values in most
  circumstances. Only change them if you have a specific need.

.. warning::

  If you set or change any of these variables, rebuild your images with
  ``docker compose build``.

BUILDER_BASE_IMAGE (optional)
  The name of the image to use in the build stage of the multi-stage Dockerfile.
  Use this to override the default value if you need to use a custom image.
  Reasons to do this may include that the packages you want to install require certain
  librairies, or you need certain SSL certificates installed. Note: you must use a
  python 3.12-based image. Defaults to ``ghcr.io/astral-sh/uv:0.12-python3.12-trixie-slim``.

RUNTIME_BASE_IMAGE (optional)
  The name of the image to use in the runtime stage of the build. A reason for
  this might be that the packages you import in your composite tests need some
  runtime dependencies installed in the container. Note: you must use a python
  3.12-based image. Defaults to ``python:3.12-slim-trixie``.

HOST_UID (optional)
  Use this to override the default value for user id in the containers. Normally,
  you want this to match the UID on the host to have read/write permissions in
  bind mounts. Defaults to ``999`` when running in production, and to your current
  UID when running in development.

HOST_GID (optional)
  Use this to override the default value for group id in the containers. Normally,
  you want this to match the GID on the host to have read/write permissions in
  bind mounts.  Defaults to ``999`` when running in production, and to your current
  GID when running in development.


Building the QATrack+ Image with Extra Python Packages
......................................................

If you'd like to be able to use in your composite tests python packages that
do not already come installed with QATrack+, you can create a
``requirements.txt`` file under ``deploy/docker/user-requirements/``.

A ``requirements.txt.example`` file exists under ``deploy/docker/user-requirements/``,
which you can copy and edit to your liking.

Specify each of your custom requirements, as described in the
`Python requirements file format <https://pip.pypa.io/en/stable/reference/requirements-file-format/>`_.

You must then rebuild the image.

.. warning::

  If your requirements conflict in any way with the QATrack+ core dependencies,
  the build will fail.


PostgreSQL Settings
^^^^^^^^^^^^^^^^^^^

POSTGRES_USER (required)
  The user name for connecting to the DB. **You should change this to the user name you want.**

POSTGRES_PASSWORD (required)
  The password for connecting to the DB. **You should change this to a strong password.**

POSTGRES_DB (required)
  The database name to use. Defaults to ``qatrackplus``.

POSTGRES_HOST_ADDRESS (optional)
  The address on which the DB will be published. Defaults to ``127.0.0.1``, which
  means the DB is only accessible from the loopback interface on the host running
  the postgres service. This makes the DB accessible from external clients running
  on remote hosts through SSH tunneling.

POSTGRES_HOST_PORT (optional)
  The port on which the DB will be accessible. Defaults to ``5434``.


NGINX Settings
^^^^^^^^^^^^^^

NGINX_SERVER_NAME (optional)
  Maps to the ``server_name`` directive of the NGINX configuration. **In general,
  you do not need to provide a value for this** since a value for ``server_name``
  will be derived from Django's ``ALLOWED_HOST``. If you want to, you may specify
  you own value for ``server_name`` by using ``NGINX_SERVER_NAME``. However, if
  you are using ``'*'`` in ``ALLOWED_HOST``, you must supply your own value for
  ``server_name`` by using ``NGINX_SERVER_NAME``.

NGINX_CLIENT_MAX_BODY_SIZE (optional)
  Controls the maximum size of uploaded files. Defaults to ``100m``.

SSL_DIR (optional)
  For a HTTPS configuration, pass the path to the directory on the host where
  SSL certificate and SSL certificate key are stored.

NGINX_SSL_CERTIFICATE_FILE (optional)
  For a HTTPS configuration, set to the file name of the SSL certificate file in
  ``SSL_DIR``.

NGINX_SSL_CERTIFICATE_KEY_FILE (optional)
  For a HTTPS configuration, set to the file name of the SSL certificate key file
  in ``SSL_DIR``.

.. note::
  ``SSL_DIR``, ``NGINX_SSL_CERTIFICATE_FILE`` and ``NGINX_SSL_CERTIFICATE_KEY_FILE``
  are all required to be set when QATrack+'s ``HTTP_OR_HTTPS`` variable is set to
  ``https``.
