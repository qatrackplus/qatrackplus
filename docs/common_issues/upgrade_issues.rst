.. _upgrade_issues:

Upgrade Issues
==============

This page collects problems that users commonly encounter while upgrading
QATrack+ from one version to another.

----

.. _upgrade_migration_conflict:

Migration Conflict After Upgrade
---------------------------------

**Symptom**

After upgrading and running ``python manage.py migrate`` you see::

   CommandError: Conflicting migrations detected; multiple leaf nodes
   in the migration graph.

**Cause**

A locally applied migration conflicts with a migration introduced in the new
release, or a third-party plugin introduced a conflicting migration.

**Solution**

1. Check the conflicting apps::

      python manage.py migrate --plan 2>&1 | grep "Conflicting"

2. If the conflict is in a QATrack+ built-in app, open a
   `GitHub issue <https://github.com/qatrackplus/qatrackplus/issues>`_ with
   the output of ``python manage.py showmigrations``.

3. If the conflict was introduced by a local customisation, roll back the
   local migration::

      python manage.py migrate <app_name> <previous_migration_number>

4. Re-run ``python manage.py migrate`` after resolving the conflict.

----

.. _upgrade_static_outdated:

Browser Shows Old Interface After Upgrade
------------------------------------------

**Symptom**

After upgrading QATrack+ the interface looks like the old version or parts of
the page are broken, even though the server is running the new version.

**Cause**

The browser is caching old static files (CSS/JavaScript) or ``collectstatic``
was not re-run after the upgrade.

**Solution**

1. Re-run ``collectstatic``::

      python manage.py collectstatic --noinput

2. Restart the application server (gunicorn/uWSGI/IIS).

3. Ask users to hard-refresh their browser (``Ctrl+Shift+R`` / ``Cmd+Shift+R``)
   or clear the browser cache.

----

.. _upgrade_settings_changed:

New Setting Required After Upgrade
------------------------------------

**Symptom**

QATrack+ starts but immediately raises an ``ImproperlyConfigured`` error or a
``KeyError`` referencing a setting name.

**Cause**

The upgrade introduced a new required setting that is missing from your
``local_settings.py``.

**Solution**

1. Read the :doc:`/release_notes` for the version you upgraded to. New required
   settings are listed there.

2. Compare your ``local_settings.py`` to
   ``qatrack/local_settings.example.py`` and add any missing settings.

3. Restart the application server.

----

.. _upgrade_pip_dependency_conflict:

pip Dependency Conflict After Upgrade
--------------------------------------

**Symptom**

After running ``pip install -r requirements.txt`` during an upgrade you see::

   ERROR: pip's dependency resolver does not currently take into account
   all the packages that are installed.

or a package fails to install because of an incompatible version of another
package.

**Solution**

1. Upgrade using a fresh virtual environment to avoid conflicts with packages
   from the previous installation::

      python -m venv venv_new
      source venv_new/bin/activate
      pip install -r requirements.txt

2. Update your service files (systemd unit, IIS application pool, etc.) to
   point to the new virtual environment path.

3. Re-run ``collectstatic`` and ``migrate`` in the new environment before
   restarting the server.
