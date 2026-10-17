Running for Development, Testing or Debugging
---------------------------------------------

Running the Docker deployment for development, testing or debugging involves
using the ``compose.dev.yaml`` file overriding ``compose.yaml``, which provides
the production configuration.

To do so, use ``docker compose -f compose.yaml -f compose.dev.yaml`` instead of 
``docker compose``.

A convenient way to use the development overrides for your current terminal
session is to set the ``COMPOSE_FILE`` environment variable:

.. code-block:: console

    $ export COMPOSE_FILE=compose.yaml:compose.dev.yaml

Once this is set, you can simply use ``docker compose`` to apply the development
overrides.

The main characteristics of the default development setup are:
  * Strict hostname matching to what is set in ``ALLOWED_HOSTS`` plus
    ``localhost`` and ``127.0.0.1``, for convenience.
  * The QATrack+ source code on the host is mounted in the containers.
  * Django development server instead of Gunicorn. The development server will serve
    static files and detect any changes to ``*.py`` files, automatically restarting.
    A manual refresh in the browser is needed when ``*.js`` or ``*.html`` files are
    changed.
  * Developement dependencies are installed on the django image.
  * In Django, ``DEBUG`` is set to ``True``.
  * The Django debug toolbar is enabled (``DEBUG_TOOLBAR = True``).
  * Docker named volumes used for persistent storage of DB, backups, media files and ``secret_key.txt``.
  * PostgreSQL published on ``127.0.0.1:5434`` on the host.
