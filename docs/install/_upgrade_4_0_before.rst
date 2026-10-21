.. This file is a fragment, pulled into each platform's upgrade guide with
   `.. include::`. It is excluded from the build in conf.py, because an included file
   that is also read as a document has every label in it reported as a duplicate.
   
   It holds what is true of the release regardless of how QATrack+ is deployed, so that
   the per-platform guides differ only where the commands differ - and so that next
   patch's notes are written once rather than three times.

Before you start
----------------

Back up your database, your ``qatrack/media`` folder and your ``local_settings.py``,
as you would for any upgrade.

.. dropdown:: Check that your existing backups contain a database
    :color: warning
    :icon: alert

    Before this release ``manage.py backup_site`` skipped the database on MySQL -
    and on any engine it does not implement - while still reporting success. A backup
    set could therefore hold media and settings and no database at all.

    **Look inside your most recent backup before relying on it.** For MySQL, use
    ``mysqldump``.

    From 4.0.1 the command names the engine it cannot handle rather than passing
    silently - **but it still exits zero**, so anything scheduled around its exit
    status cannot tell the difference. Check the output, or check that a database
    file is there.

    **It writes a database backup on SQL Server and SQLite only.** PostgreSQL is not
    one of them: the command has always reported that it cannot, so if your
    PostgreSQL site has been relying on it, check now. Use ``pg_dump``, or the
    Docker backup script, which does.

What needs your attention in this release
-----------------------------------------

Most of 4.0.1 is bug fixes that need nothing from you. These four do:

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
correct as of 4.0.1, and removing your copy means you also receive any future
correction.

Two older values are worth recognising, because both are worse than the current default:

.. code-block:: python

    # the commented example the installation templates carried from 2018
    LOGIN_EXEMPT_URLS = [r"^qatrack/accounts/", r"qatrack/api/*"]

    # the shipped default before 4.0.1
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
