Docker Deployment Layout
========================

This section is meant to give an overview of how the Docker deployment is set up.

Layout Under ``deploy/docker``
------------------------------

Here is a brief description of how the Docker deployment is laid out:
  * ``.env.example``: A self-documenting example file defining the environment variables
    for configuring the deployment.
  * ``.env``: The file containing the values of the environment variables. You must create
    this file yourself.
  * ``compose.yaml``: The production defaults.
  * ``compose.dev.yaml``: Development overrides (e.g. binding local source code, running
    the Django development server).
  * ``django/``: Multi-stage Dockerfile and entrypoint script for the Django app.
  * ``nginx/``: NGINX configuration and server blocks.
  * ``backup/``: A lightweight Alpine container that automatically runs database and
    media backups via cron.
  * ``user-requirements/``: A directory to define any additional python package
    requirements to be installed when building the django service image. Useful
    if you want to include extra python packages you need when running composite
    tests.

**The setup is meant to be run with** ``docker compose`` **from the** ``deploy/docker``
**directory**.

Service Topology
----------------

The Docker deployment consists of five services. The arrows indicate
healthcheck-based ``depends_on`` relationships.

.. code-block:: text

                         +-------------------+
                         |     postgres      |
                         |     database      |
                         +-------------------+
                              ^           ^
                             /             \
                healthy     /               \     healthy
                           /                 \
              +-------------------+    +-------------------+
              |      django       |    |      backup       |
              |  QATrack+ web app |    | scheduled backups |
              +-------------------+    +-------------------+
                    ^         ^
                   /           \
          healthy /             \ healthy
                 /               \
      +-------------------+  +-------------------+
      |       nginx       |  |     django-q      |
      |   HTTP / HTTPS    |  | background tasks  |
      +-------------------+  +-------------------+


Persistent Storage
------------------

By default, persistent data is stored in Docker named volumes. Each persistent
storage location can instead use a bind mount by setting the corresponding
environment variable in ``.env``.

.. code-block:: text

                              Persistent storage
                                     |
                    +----------------+----------------+
                    |                                 |
             Environment variable        Environment variable unset
                    |                                 |
                    v                                 v
                Bind mount                     Docker volume


    POSTGRES_DATA_DIR
            |
            +-----> [ bind mount | postgres-volume ]
                                  |
                                  v
                             +----------+
                             | postgres |
                             +----------+
                        /var/lib/postgresql/data


    MEDIA_DIR
       |
       +----------> [ bind mount | media-volume ]
                                  |
                    +-------------+-------------+-------------+
                    |             |             |             |
                    v             v             v             v
                 django       django-q        nginx         backup
                                              (ro)               
                                  /app_data/media


    BACKUPS_DIR
          |
          +-------> [ bind mount | backups-volume ]
                                  |
                                  v
                              +--------+
                              | backup |
                              +--------+
                               /backups


    USER_DATA_DIR
           |
           +------> [ bind mount | user-data-volume ]
                                  |
                          +-------+-------+
                          |               |
                          v               v
                       django          django-q
                                         (ro)
                              /user_data
             (secret_key.txt -- only if SECRET_KEY is unset)


    static-volume
          |
          |  Docker volume only
          |
          +---------------------+
          |                     |
          v                     v
       django                  nginx
                               (ro)
                      /app_data/static

``POSTGRES_DATA_DIR``, ``MEDIA_DIR``, ``BACKUPS_DIR`` and ``USER_DATA_DIR``
control whether the corresponding persistent storage uses a bind mount or a
Docker named volume. When an environment variable is unset, the named volume
shown above is used by default.

``static-volume`` is always a Docker named volume. It is shared between Django,
which populates it with static assets, and NGINX, which mounts it read-only to
serve those assets.
