.. A fragment. See the note at the top of _upgrade_4_0_1_before.rst.

After upgrading
---------------

**Check a date on a form.** Open a form that has a pre-filled date and confirm it
shows the date you expect. That is the fix this release exists for, and it is visible
in ten seconds. The quickest two:

- **a new fault**, at ``/faults/create/``, whose *Occurred* field pre-fills with now;
- **an existing service event**, at ``/servicelog/event/edit/<id>/``, which shows a
  date that was stored before the upgrade rather than today's.

Both should read ``YYYY-MM-DD``, and the service event's time should be the local time
you recorded it at, not an offset from it.

**On SQL Server, confirm the constraints came back:**

.. code-block:: shell

    python manage.py check --database default

should now report nothing. **The** ``--database`` **is not optional here** - plain
``manage.py check`` cannot see these warnings at all, and will say there are no issues
whether or not every constraint is missing.

If it still reports ``qatrack.W014`` for a table, that constraint was skipped because
of duplicate rows. ``manage.py check_unique_constraints`` names them, and once they are
resolved the repair can be run again by reversing the migration for that app and
applying it forward:

.. code-block:: shell

    python manage.py migrate parts 0018_v4_0_final
    python manage.py migrate

Reversing removes the constraints that app's migration added and applying it forward
puts back every one it can - including the one that was skipped. A plain ``migrate``
on its own will not do it, because the migration is already recorded as applied.

**Confirm your backups once more** - if you act on one thing after this release,
make it reading the output of your next backup run rather than its exit status.

Running the test suite against an installed server
--------------------------------------------------

You do not need to, and most sites never will. It is worth knowing how, because
"the suite passes on my server" is the most direct answer to *did this upgrade
land cleanly*, and two things stop it working on a deployment that was set up by
following this guide.

**The database user cannot create the test database.** ``pytest`` reads your
``local_settings.py``, so it talks to your real database server, and then asks it
for a *second*, temporary database to run against. The user this guide creates
owns the QATrack+ database and nothing else, so that request is refused:

.. code-block:: text

    # PostgreSQL
    permission denied to create database
    # SQL Server
    CREATE DATABASE permission denied in database 'master'. (262)

Grant it for the run and take it away afterwards, rather than leaving it in
place:

.. code-block:: bash

    # PostgreSQL
    sudo -u postgres psql -c "alter role qatrack createdb"
    # ... run the suite ...
    sudo -u postgres psql -c "alter role qatrack nocreatedb"

.. code-block:: sql

    -- SQL Server
    ALTER SERVER ROLE [dbcreator] ADD MEMBER [qatrack];
    -- ... run the suite ...
    ALTER SERVER ROLE [dbcreator] DROP MEMBER [qatrack];

**The GUI tests need a browser.** Around 35 of them drive a real one, and on a
server with none installed they error at setup rather than being skipped. That is
not a failure of your installation. Deselect them by marker - ignoring the file
they mostly live in is not enough, because other test modules import its base
class and define browser-driven tests of their own:

.. code-block:: bash

    .venv/bin/python -m pytest -m "not selenium"

On Windows that is ``.venv\Scripts\python.exe -m pytest -m "not selenium"``, and the
grant above is the SQL Server one.

.. warning::

    **Your own settings are in force while the suite runs**, because ``pytest``
    loads ``qatrack.settings`` and therefore your ``local_settings.py``. A site
    with local modifications can see large numbers of failures that say nothing
    about QATrack+ - on the public demo server, a local restriction on calculated
    tests failed **140** of them, all for the same reason.

    If that happens, put the differing settings in a module of their own and
    point the run at it, rather than editing the settings your site is serving
    with:

    .. code-block:: python

        # qatrack/my_test_settings.py
        from qatrack.settings import *  # noqa

        SOME_LOCAL_RESTRICTION = False

    .. code-block:: bash

        .venv/bin/python -m pytest --ds=qatrack.my_test_settings

Upgrading an installation you have modified
-------------------------------------------

If you have edited files inside ``qatrack/``, check whether the upgrade touches
the same ones before you pull. ``git status`` lists what you changed; keep a copy
of the diff somewhere outside the checkout, because an upgrade that edits the same
file will make you re-apply it by hand rather than merging it for you.

**If you have already pulled, nothing is lost.** ``git pull`` refuses to overwrite a
file you have modified, so either it completed and your edits are still there, or it
stopped and told you which files it would have overwritten. ``git status`` and
``git diff`` still answer the same question afterwards as before.

4.0.2 changes ``qatrack/qatrack_core/apps.py``, which is a common place for sites
to add start-up code of their own.
