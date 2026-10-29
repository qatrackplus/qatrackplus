.. _linux_upgrade_from_4_0_1:

Upgrading an Ubuntu Linux 4.0.1 installation to 4.0.2
=====================================================

4.0.2 is a patch release that **does run database migrations**, unlike 4.0.1. On
Ubuntu Linux the upgrade is a backup, a code update, a dependency sync, the
migrations and a restart:

1. Stop the background services
2. **Back up the database, and confirm the backup opens**
3. ``git fetch`` and ``git pull``
4. ``uv sync`` with your database's extra
5. ``python manage.py check --database default``
6. ``python manage.py migrate`` and ``python manage.py collectstatic``
7. Start the services again

You never name a version. The installation guide checks out the ``releases/4.0``
*branch* rather than a version tag, so the branch carries each patch as it is released
and a ``git pull`` is all that moves you between them.

**These steps apply to any 4.0.x patch**, not only this one. What changes between
patches is in the next section.

.. note::

    **Run these commands as the account that owns the installation** - the
    ``qatrack`` user in this guide's examples. Every command below uses
    ``~/web/qatrackplus``, which only resolves for that account, and the
    ``pg_dump`` in the backup step authenticates by *being* it. If you are at a
    root shell, ``sudo -u qatrack -i`` gets you there; the account still needs to
    be able to ``sudo``, because stopping and starting the services does.

.. include:: _upgrade_4_0_1_before.rst

Running the upgrade
-------------------

Stop the services first, so nothing runs mid-upgrade:

.. code-block:: bash

    sudo supervisorctl stop gunicorn django-q2
    sudo service nginx stop

.. warning::

    ``gunicorn`` matters as much as ``django-q2`` here. Supervisor runs it as its
    own program, so stopping nginx does not stop it: it keeps its Python already
    imported while you replace the dependencies and the templates underneath it.
    What you get is old code serving new templates and new static files, which
    fails in ways that look nothing like an upgrade problem — and this release
    changes the date formats every form renders, so the symptom is dates that do
    not match the release notes.

Back up the database now, with the services stopped, and confirm the backup is
readable before you go any further — see :ref:`qatrack_backup`:

.. code-block:: bash

    pg_dump -U qatrack -Fc qatrackplus > ~/qatrackplus-pre-4.0.2.dump
    pg_restore --file=/dev/null ~/qatrackplus-pre-4.0.2.dump && echo "backup reads OK"

.. note::

    **Neither backup command asks for a password, and that is why the account
    matters.** ``pg_dump -U qatrack`` connects over the local socket, where
    PostgreSQL matches the operating-system user to the database role of the same
    name - so it works because you *are* ``qatrack``. Run it from any other
    account, root included, and it is refused. From elsewhere, either switch user
    first, or add ``-h 127.0.0.1`` and give the password from
    ``local_settings.py``, which is what the MySQL line below does with ``-p``.

On MySQL, the equivalent. ``--single-transaction`` keeps the dump consistent, and the
last line a complete ``mysqldump`` writes is ``-- Dump completed``, so its absence is
how you tell a truncated file from a finished one:

.. code-block:: bash

    mysqldump -u qatrack -p --single-transaction --routines qatrackplus \
        > ~/qatrackplus-pre-4.0.2.sql
    tail -1 ~/qatrackplus-pre-4.0.2.sql | grep -q 'Dump completed' && echo "backup reads OK"

.. warning::

    **If this site has backup sets from before 4.0.1, do not rely on them here.**
    ``manage.py backup_site`` skipped the database silently on MySQL and still reported
    success, so an older set can hold media and settings and no database at all - see
    :ref:`qatrack_backup`. Take the dump above instead.

Back up the uploaded files too. **They are not in the database**, and a dump plus a
copy of ``local_settings.py`` is not a complete set without them:

.. code-block:: bash

    tar -czf ~/qatrackplus-media-pre-4.0.2.tar.gz -C ~/web/qatrackplus qatrack/media

``manage.py backup_site`` archives the same folder on every engine if you would
rather use it, but check **where** it put the file before you trust it: ``BACKUP_DIR``
is a Windows path in the shipped settings, so set it in ``local_settings.py`` on a
Linux server. :ref:`qatrack_backup` says what a complete set contains.

Fetch the new version:

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
    uv sync --extra postgres --no-dev

``--no-dev`` matters as much here as it does at installation, and for the same
reason: without it ``uv`` installs the ``dev`` group onto your server as well -
around 200 packages including pytest, selenium, sphinx and django-debug-toolbar,
none of which serve anything. Leave it off only if you intend to run the test suite
on this machine, as described at the end of this page.

.. dropdown:: For MySQL
    :color: warning

    .. code-block:: bash

        cd ~/web/qatrackplus
        uv sync --extra mysql --no-dev

Check the installation before touching the database. ``--database default`` runs the
checks that need a connection as well as the ones that do not; on PostgreSQL and MySQL
they find nothing, because the constraint loss this release repairs only happened on
SQL Server:

.. code-block:: bash

    python manage.py check --database default

Then run the migrations and collect the static files. **This release has migrations**,
so ``migrate`` will report work done. ``collectstatic`` is still required - this
release changes JavaScript and templates - though it will usually report only a file
or two copied, which is normal and not a sign it did nothing:

.. code-block:: bash

    python manage.py migrate
    python manage.py collectstatic --noinput

``--noinput`` answers the *"This will overwrite existing files! Are you sure you want
to do this?"* prompt that ``collectstatic`` otherwise stops at and waits for. Leave it
off if you would rather answer it yourself - but a script that pipes the output will
hide the question while still waiting for it.

Restart — the application servers first, so nginx has something to proxy to the
moment it comes back:

.. code-block:: bash

    sudo supervisorctl start gunicorn django-q2
    sudo service nginx start

Confirm both are running, **and that the site itself answers**, before you call the
upgrade done. ``supervisorctl`` reporting ``RUNNING`` means the processes started, not
that a request reaches them:

.. code-block:: bash

    sudo supervisorctl status
    curl -I http://localhost/

Expect ``200`` or a redirect to your login page. A ``400`` means the hostname you
asked for is not in ``ALLOWED_HOSTS`` - a settings answer, not a failed upgrade - so
try your site's own name. Anything from nginx about a bad gateway means gunicorn did
not come back; ``logs/gunicorn.log`` says why.

.. include:: _upgrade_4_0_1_after.rst
