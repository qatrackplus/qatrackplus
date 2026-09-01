.. _installation_issues:

Installation Issues
===================

This page collects problems that users commonly encounter while installing
QATrack+ for the first time.

----

.. _missing_migrations:

Missing or Unapplied Migrations
--------------------------------

**Symptom**

After running ``python manage.py migrate`` the application shows a
``ProgrammingError`` or ``OperationalError`` mentioning a missing table or
column when you first open QATrack+ in a browser.

**Cause**

A migration was added between the version of QATrack+ you installed and the
database schema that already existed.

**Solution**

1. Check which migrations are pending::

      python manage.py showmigrations | grep "\[ \]"

2. Apply all pending migrations::

      python manage.py migrate

3. If a migration fails with a conflict error, run::

      python manage.py migrate --run-syncdb

4. Restart the application server.

**See also**

* `Django migration docs <https://docs.djangoproject.com/en/stable/topics/migrations/>`_
* `QATrack+ install guide <https://docs.qatrackplus.com/en/stable/install/install.html>`_

----

.. _static_files_not_loading:

Static Files Not Loading (CSS/JS Missing)
------------------------------------------

**Symptom**

After installation the QATrack+ interface loads but has no styling — it looks
like plain HTML. Images and JavaScript widgets are also missing.

**Cause**

The ``collectstatic`` step was skipped or the web server is not configured to
serve files from the ``STATIC_ROOT`` directory.

**Solution**

1. Run the static file collector::

      python manage.py collectstatic --noinput

2. Confirm that your web server (nginx/Apache/IIS) is configured to serve the
   ``STATIC_ROOT`` directory at the ``STATIC_URL`` path defined in
   ``local_settings.py``.

3. On Ubuntu with nginx, the relevant block looks similar to::

      location /static/ {
          alias /var/www/qatrackplus/static/;
      }

4. Reload or restart the web server after any configuration change.

**See also**

* :ref:`Linux installation guide <linux_install>`
* `Django static files howto <https://docs.djangoproject.com/en/stable/howto/static-files/>`_

----

.. _db_connection_refused:

Database Connection Refused
----------------------------

**Symptom**

QATrack+ fails to start and the logs show::

   django.db.utils.OperationalError: could not connect to server: Connection refused

**Cause**

The database server is not running, or the connection settings in
``local_settings.py`` are incorrect.

**Solution**

1. Verify the database service is running:

   * **PostgreSQL (Ubuntu)**::

         sudo systemctl status postgresql

   * **SQL Server (Windows)**: check SQL Server Configuration Manager.

2. Confirm the ``DATABASES`` block in ``local_settings.py`` uses the correct
   ``HOST``, ``PORT``, ``NAME``, ``USER``, and ``PASSWORD``.

3. Test the connection manually::

      # PostgreSQL
      psql -h <HOST> -U <USER> -d <DATABASE>

4. If using a socket connection on Linux, ensure the socket path is correct or
   switch to a TCP connection by setting ``HOST = '127.0.0.1'``.

----

.. _pip_install_fails:

pip Install Fails with Compilation Errors
------------------------------------------

**Symptom**

Running ``pip install -r requirements.txt`` fails with errors such as::

   error: command 'gcc' failed with exit status 1

or::

   Microsoft Visual C++ 14.0 or greater is required.

**Cause**

Some Python packages include C extensions that must be compiled. The required
compiler or development headers are not installed.

**Solution**

* **Ubuntu/Debian**::

      sudo apt-get install python3-dev build-essential libpq-dev

* **Windows**: Install
  `Microsoft C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_
  and ensure it is on your ``PATH``.

After installing the prerequisites, re-run ``pip install -r requirements.txt``.
