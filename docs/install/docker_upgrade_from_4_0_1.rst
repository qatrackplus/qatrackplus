.. _docker_upgrade_from_4_0_1:

Upgrading an existing Docker 4.0.x installation
===============================================

This release reorganises the Docker deployment, and **it does carry database
migrations** - eight of them, holding 195 schema operations. They are field-state
changes that 4.0 never recorded, so they alter no data, and they have been run
against a real site's database (1.6 million test instances, 14 seconds) as well
as a small one. But the upgrade is not the pure code change the 4.0.0 → 4.0.1 one
was.

**Three things will stop it part-way if you are not expecting them**: a file that
used to be tracked in git, a setting that 4.0.1 could do without, and the fact
that the container no longer runs as root.

Read this page before you start. Every step below was run as written on a clean
Ubuntu Server, upgrading a 4.0.1 Docker installation built from the tag
(2026-10-19), and on a 4.0.1 stack with a restored clinical database (2026-10-19).

What changed
------------

* The containers run as the unprivileged user ``uid 999`` instead of root.
* Media and static files are mounted at ``/app_data/media`` and
  ``/app_data/static`` rather than under ``/usr/src/qatrackplus``.
* ``deploy/docker/.env`` is no longer tracked in git. It holds your passwords,
  so it should never have been.
* ``compose.override.yaml`` — which docker compose loaded automatically, giving
  every installation the development bind mount — is now ``compose.dev.yaml``,
  loaded only when you ask for it.
* There is a new ``django-q`` service running the task cluster, and a
  ``user-data`` volume holding ``secret_key.txt``.
* The secret key is generated once and kept in the ``user-data`` volume unless
  you set ``SECRET_KEY`` in ``.env``. Everyone is signed out on the first
  restart after the upgrade; accounts and passwords are unaffected.

.. include:: _upgrade_4_0_before.rst

Before you start
----------------

Take a backup, and keep a copy of your ``.env`` somewhere outside the
repository — you are about to need it:

.. code-block:: bash

    cd ~/web/qatrackplus/deploy/docker
    cp .env ~/qatrackplus-env-backup
    docker compose exec backup /backup.sh

Step 1: let git replace the tracked ``.env``
--------------------------------------------

``git pull`` stops with::

    error: Your local changes to the following files would be overwritten by checkout:
        deploy/docker/.env
    Please commit your changes or stash them before you switch branches.
    Aborting

This is the tracked example ``.env`` the old deployment shipped, with your
edits in it. With the copy you made above, discard it and fetch the new version:

.. code-block:: bash

    cd ~/web/qatrackplus
    git checkout -- deploy/docker/.env
    git fetch origin --tags
    git checkout <the new tag>
    cp ~/qatrackplus-env-backup deploy/docker/.env

.. note::

    ``git pull`` is not the command here, even though the 4.0.0 → 4.0.1 page used
    it. The setup page has you check out a **tag**, so your HEAD is detached and a
    pull answers ``You are not currently on a branch.`` Fetch and check out the
    new tag instead - the ``.env`` refusal above then appears exactly as
    described.

Your old settings keep their meanings: ``POSTGRES_USER``,
``POSTGRES_PASSWORD``, ``POSTGRES_DB``, ``ALLOWED_HOSTS`` and
``CSRF_TRUSTED_ORIGINS`` all mean what they did.
``deploy/docker/.env.example`` documents what you can now add, including
``SITE_NAME``, ``SITE_DOMAIN`` and ``SECRET_KEY``.

Step 1b: make sure ``.env`` has ``ALLOWED_HOSTS``
--------------------------------------------------

**If your ``.env`` has no ``ALLOWED_HOSTS`` line, add one now.** 4.0.1 fell back
to ``localhost,127.0.0.1`` when it was unset; this release requires it, and
without it the django container stops with::

    ValueError: Required environment variable is missing, or has empty value: ALLOWED_HOSTS

and restarts until you intervene, with ``docker compose up -d`` exiting non-zero.

This bites precisely the site this page is written for. 4.0.1's *tracked* ``.env``
- the one you edited and just restored - has no such line, while a site that
copied ``.env.example`` instead already has ``ALLOWED_HOSTS=*``. Set it to the
names the site is reached by:

.. code-block:: bash

    printf '\nALLOWED_HOSTS=qatrackplus.yourdomain,127.0.0.1\n' >> deploy/docker/.env

.. tip::

    Set ``SECRET_KEY`` in the same edit if it is not there. Otherwise the key is
    generated on the first boot - including a boot that then fails - and the
    notice saying so goes with the container that ``docker compose down`` removes
    in Step 2. Everyone is signed out either way, which this page says below, but
    you will not have seen the message explaining it.

Step 2: give the new container user ownership of its volumes
-------------------------------------------------------------

The old image ran as root, so everything in your media and static volumes is
owned by root. The new one runs as ``uid 999`` and will not be able to write
there. If you skip this step the django container fails its system checks,
exits, is restarted by docker, and fails again — a crash loop whose logs read::

    ERRORS:
    ?: (qatrack.E001) The Django server process does not have write permissions to '/app_data/media'.

and ``docker compose up -d`` exits non-zero with ``dependency failed to start:
container qatrackplus-django-1 is unhealthy``.

So, with the stack stopped, hand both volumes to ``999``:

.. code-block:: bash

    cd ~/web/qatrackplus/deploy/docker
    docker compose down
    docker run --rm \
        -v qatrackplus_media-volume:/media \
        -v qatrackplus_static-volume:/static \
        alpine chown -R 999:999 /media /static

Use ``docker volume ls`` to confirm the volume names; they are prefixed with
the compose project name. If you use bind mounts (``MEDIA_DIR``), run
``sudo chown -R 999:999`` on those directories instead.

.. note::

    999 is the default. If you build the image with ``HOST_UID``/``HOST_GID``
    set to something else, use that instead — ``docker compose run --rm django
    id`` prints what the image actually uses.

Running the upgrade
-------------------

.. code-block:: bash

    cd ~/web/qatrackplus/deploy/docker
    docker compose build
    docker compose up -d
    docker compose exec django python manage.py check
    docker compose exec django python manage.py migrate

The first boot is slower than later ones — the entrypoint runs migrations and
collects static files before the web server binds — and ``docker compose up
-d`` waits for the health check to pass, so expect it to sit for a minute or
two before returning.

Checking the result
-------------------

``manage.py check`` should report no issues, and all five services should be
``healthy``:

.. code-block:: bash

    docker compose ps

Then sign in. You will be asked for your password again even if you had a
session open, because the secret key is new.

.. include:: _upgrade_4_0_after.rst
