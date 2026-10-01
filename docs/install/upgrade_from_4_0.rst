.. _upgrade_from_4_0:

Upgrading from v4.0.0 to v4.0.1
===============================

v4.0.1 is a patch release. It contains **no database migrations**, so the upgrade is a
code update, a dependency sync and a restart:

**stop the services → ``git fetch`` → ``git pull`` → ``uv sync`` → ``check`` → restart.**

Because the installation guides check out the ``releases/4.0`` *branch* rather than a
version tag, you never name a version when upgrading within the v4.0 series — the
branch carries each patch as it is released. **The steps on this page apply to any
v4.0.x patch**, not only this one; the release-specific notes are in the next section.

.. note::

    The service and scheduled task names stopped carrying version numbers in v4.0.0
    precisely so that patch upgrades like this one would not require renaming
    anything. If you upgraded to v4.0.0 from v3.x, your service is called
    *QATrack+ Web Service* and your scheduled task *QATrack+ Django Q Cluster*.

Before you start
----------------

Back up your database, your ``qatrack/media`` folder and your ``local_settings.py``,
as you would for any upgrade.

.. warning::

    **If your database is MySQL, check that your existing backups actually contain
    a database.** Before this release ``manage.py backup_site`` skipped the database
    on MySQL and on any engine other than PostgreSQL and SQLite, and still reported
    success — so a backup set could contain media and settings and no database at
    all. Look inside your most recent backup before relying on it. From v4.0.1 the
    command says which engine it cannot handle and fails that step instead of
    passing silently.

    For MySQL, use ``mysqldump``.

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

Check ``LOGIN_EXEMPT_URLS`` if you have overridden it
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

    This is the one item on this page with a security consequence. If your
    ``local_settings.py`` sets ``LOGIN_EXEMPT_URLS``, **your copy overrides the
    corrected list and still has the original fault.**

The shipped list previously contained entries written as though they were globs:

.. code-block:: python

    LOGIN_EXEMPT_URLS = [r"^favicon.ico$", r"^accounts/", r"api/*", r"^oauth2/*", r"^i18n/"]

These are *regular expressions*, not globs. ``api/*`` does not mean "anything under
``api/``" — as a regex it reads as ``api`` followed by zero or more slashes, so it also
exempted ``apifoo``, ``api_secret`` and any other path merely beginning with those three
letters. ``^favicon.ico$`` left the ``.`` unescaped, so it matched any single character.

The corrected list, which v4.0.1 ships:

.. code-block:: python

    LOGIN_EXEMPT_URLS = [
        r"^favicon\.ico$",
        r"^accounts/",
        r"^api(/|$)",
        r"^oauth2(/|$)",
        r"^i18n/",
        r"^jsi18n/",
    ]

If you have no ``LOGIN_EXEMPT_URLS`` in ``local_settings.py`` you have the corrected
list already and need do nothing.

``jsi18n`` is listed separately from ``i18n`` because the URL is ``/jsi18n/``, which
``^i18n/`` does not match — that omission is why client-side translations never loaded
for users who were not signed in.

See :ref:`qatrack-config` for the full explanation, including why overriding this
setting replaces the list rather than adding to it.

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

**Check that your group permissions include the** ``view`` **permissions.** This is
worth doing once, and it matters most if your groups were created in v3.x.

Django gained a separate ``view`` permission for every model in version 2.1. Groups
set up before that have ``change`` permissions but were never granted the matching
``view`` ones, because they did not exist yet. QATrack+'s own admin pages hide this,
because Django treats ``change`` as implying ``view`` — but some admin widgets check
for ``view`` alone, and a group without it can find that a field renders blank with
no error.

In the admin, under *Authentication and Authorization* → *Groups*, open each group
and confirm that wherever it has *Can change X* it also has *Can view X*.

**Confirm your backups.** If you act on only one thing in this release, make it the
MySQL backup warning at the top of this page.
