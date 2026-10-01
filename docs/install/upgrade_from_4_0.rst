.. _upgrade_from_4_0:

Upgrading from v4.0.0 to v4.0.1
===============================

v4.0.1 is a patch release containing **no database migrations**. The upgrade is a code
update, a dependency sync and a restart:

1. Stop the background services
2. ``git fetch`` and ``git pull``
3. ``uv sync``
4. ``python manage.py check``
5. ``python manage.py migrate`` and ``python manage.py collectstatic``
6. Start the services again

You never name a version. The installation guides check out the ``releases/4.0``
*branch* rather than a version tag, so the branch carries each patch as it is released
and step 2 is all that is needed to move between them.

**These steps apply to any v4.0.x patch**, not only this one. What changes between
patches is the next section.

.. note::

    The service and scheduled task names stopped carrying version numbers in v4.0.0
    precisely so that patch upgrades like this one would not require renaming
    anything. If you upgraded to v4.0.0 from v3.x, your service is called
    *QATrack+ Web Service* and your scheduled task *QATrack+ Django Q Cluster*.

Before you start
----------------

Back up your database, your ``qatrack/media`` folder and your ``local_settings.py``,
as you would for any upgrade.

.. dropdown:: On MySQL, check your existing backups contain a database
    :color: danger
    :icon: alert

    Before this release ``manage.py backup_site`` skipped the database on MySQL - and
    on any engine other than PostgreSQL and SQLite - while still reporting success. A
    backup set could therefore hold media and settings and no database at all.

    **Look inside your most recent backup before relying on it.** For MySQL, use
    ``mysqldump``.

    From v4.0.1 the command names the engine it cannot handle and fails that step
    rather than passing silently.

What needs your attention in this release
-----------------------------------------

Most of v4.0.1 is bug fixes that need nothing from you. These four do:

**Python 3.12 and Django 4.2.30 or newer are now required.** The Django floor was
raised for its security fixes and Python is pinned to 3.12. ``uv sync`` below
installs the right versions; you do not need to change anything by hand.

**If you deploy with Docker, check your backup environment variables.** The backup
script now reads ``POSTGRES_DB``, ``POSTGRES_USER`` and ``POSTGRES_PASSWORD`` from
the environment instead of having the database name and user written into it. These
are the same variables the ``postgres`` service already uses, so a deployment that
sets them in its ``.env`` needs no change. One that had customised the hard-coded
values was previously dumping the wrong database, or nothing — confirm your next
backup contains what you expect.

**If you deploy with Docker, you may now set** ``CSRF_TRUSTED_ORIGINS`` **from the
environment.** It falls back to ``ALLOWED_HOSTS`` when not given. See the comments in
``deploy/docker/.env.example``.

**The** ``installfixtures`` **management command has been removed.** It loaded a
fixture set that no longer matched the schema. If you called it from a script, use
``manage.py loaddata`` with the fixtures you want instead.

Changes to ``local_settings.py``
--------------------------------

**Nothing in this release requires a change to** ``local_settings.py``. Your existing
file keeps working. There is one thing to check and two new settings you may want.

Remove ``LOGIN_EXEMPT_URLS`` if your ``local_settings.py`` sets it
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

    This is the one item on this page with a security consequence. Setting
    ``LOGIN_EXEMPT_URLS`` **replaces** the shipped list rather than adding to it, so your
    copy overrides the corrected one and keeps whatever fault it was copied with.

**If the setting appears in your** ``local_settings.py`` **, delete the whole
assignment** unless you deliberately need entries of your own. The shipped default is
correct as of v4.0.1, and removing your copy means you also receive any future
correction.

Two older values are worth recognising, because both are worse than the current default:

.. code-block:: python

    # the commented example the installation templates carried from 2018
    LOGIN_EXEMPT_URLS = [r"^qatrack/accounts/", r"qatrack/api/*"]

    # the shipped default before v4.0.1
    LOGIN_EXEMPT_URLS = [r"^favicon.ico$", r"^accounts/", r"api/*", r"^oauth2/*", r"^i18n/"]

These are *regular expressions*, not globs. ``api/*`` reads as ``api`` followed by zero
or more slashes, so it also exempts ``apifoo``, ``api_secret`` and anything else merely
beginning with those three letters. ``^favicon.ico$`` leaves the ``.`` unescaped, matching
any character. The 2018 example additionally carries a ``qatrack/`` prefix that no longer
matches anything, and omits four entries the current default has — so a site using it
requires a login for its favicon, OAuth2 and both translation catalogues.

If you do need your own entries, add them to a copy of the current default rather than an
older one:

.. code-block:: python

    LOGIN_EXEMPT_URLS = [
        r"^favicon\.ico$",
        r"^accounts/",
        r"^api(/|$)",
        r"^oauth2(/|$)",
        r"^i18n/",
        r"^jsi18n/",
        # your own entries here
    ]

See :ref:`qatrack-config` for the full explanation.

Two new settings, both optional
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**``LANGUAGE_COOKIE_AGE``** sets how long a user's language choice is remembered. It
now defaults to one year; before this release the cookie had no explicit lifetime, so
it expired with the browser session and the interface reverted to the default language
on the next visit. To shorten it:

.. code-block:: python

    LANGUAGE_COOKIE_AGE = 30 * 24 * 60 * 60   # 30 days

**``CSRF_TRUSTED_ORIGINS``** may now be set from the environment, which is mainly of
interest to Docker deployments. When the ``CSRF_TRUSTED_ORIGINS`` environment variable
is set it is read as a comma-separated list; when it is not, it is derived from
``ALLOWED_HOSTS``. You can still set it directly in ``local_settings.py`` if you prefer.
See the comments in ``deploy/docker/.env.example``.

Ubuntu Linux
------------

Stop the background services first, so no task runs mid-upgrade:

.. code-block:: bash

    sudo supervisorctl stop django-q2
    sudo service nginx stop

Fetch the new version. If you installed from the ``releases/4.0`` branch — which is
what the installation guides use — this is a ``pull``, and you do not name a version at
all:

.. code-block:: bash

    cd ~/web/qatrackplus
    git fetch origin
    git pull

.. note::

    If ``git pull`` reports that you are not on a branch, you are on a tag from an
    earlier install. ``git checkout releases/4.0`` once, and every upgrade after that is
    the ``pull`` above.

Update the Python environment. Use the extra that matches your database:

.. code-block:: bash

    cd ~/web/qatrackplus
    source .venv/bin/activate
    uv sync --extra postgres

.. dropdown:: For MySQL
    :color: warning

    .. code-block:: bash

        cd ~/web/qatrackplus
        uv sync --extra mysql

Check the installation before touching the database. This validates your settings
against the new code and is the cheapest way to catch a problem while the services are
still stopped:

.. code-block:: bash

    python manage.py check

Then run the migration step and collect the static files. **There are no migrations in
this release**, so ``migrate`` will report nothing to do — run it anyway, so that a
future release cannot find the database a step behind. ``collectstatic`` is not
optional: this release changes JavaScript and templates.

.. code-block:: bash

    python manage.py migrate
    python manage.py collectstatic

Restart:

.. code-block:: bash

    sudo service nginx start
    sudo supervisorctl start django-q2

Windows Server
--------------

Stop the scheduled task and the web service:

.. code-block:: console

    >>  Stop-ScheduledTask -TaskName "QATrack+ Django Q Cluster"
    >>  Stop-Service "QATrack+ Web Service"

Fetch the new version and update the environment. As on Linux, you do not name a
version — the ``releases/4.0`` branch you installed from carries the patch:

.. code-block:: console

    >>  cd C:\deploy\qatrackplus
    >>  git fetch origin
    >>  git pull
    >>  uv sync --exact --extra win --extra mssql

Check the installation, then run the migration step and collect static files:

.. code-block:: console

    >>  python manage.py check
    >>  python manage.py migrate
    >>  python manage.py collectstatic

Restart:

.. code-block:: console

    >>  Start-Service "QATrack+ Web Service"
    >>  Start-ScheduledTask -TaskName "QATrack+ Django Q Cluster"

Docker
------

From your ``deploy/docker`` directory:

.. code-block:: bash

    cd ~/web/qatrackplus
    git fetch origin
    git pull
    cd deploy/docker
    docker compose build
    docker compose up -d

Then check the installation and run the migration step inside the container:

.. code-block:: bash

    docker compose exec django python manage.py check
    docker compose exec django python manage.py migrate

Before restarting, re-read *What needs your attention in this release* above: the
backup script's environment variables changed in this release.

.. note::

    ``manage.py check`` reports configuration problems, not data problems — it will not
    tell you whether your backups contain a database or whether your groups have the
    permissions they need. Both are covered below.

After upgrading
---------------

**Check your group permissions**, once, if any group was created in v3.x. Under
*Authentication and Authorization* → *Groups*, confirm that wherever a group has
*Can change X* it also has *Can view X*.

.. dropdown:: Why those groups are missing it

    Django added a separate ``view`` permission per model in version 2.1, so groups set
    up before that have ``change`` without it. The admin hides this, because Django
    treats ``change`` as implying ``view`` — but some admin widgets check for ``view``
    alone, and a group lacking it sees a field render blank with no error.

**Confirm your backups** — if you act on one thing in this release, make it the MySQL
check at the top of this page.
