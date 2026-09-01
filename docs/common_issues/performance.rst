.. _performance:

Performance Issues
==================

This page collects problems related to QATrack+ being slow or unresponsive.

----

.. _slow_test_list:

Test List Pages Load Slowly
----------------------------

**Symptom**

Opening a test list or the test list overview page takes a long time
(> 5 seconds) even when only a few users are active.

**Cause**

The database has grown large and some queries are no longer efficient, or the
application server has too few worker processes.

**Solution**

1. **Add database indexes** — run ``EXPLAIN ANALYZE`` (PostgreSQL) or
   ``EXPLAIN`` (SQL Server/MySQL) on slow queries to identify missing indexes.
   QATrack+ relies on a number of indexes that should be created automatically
   by migrations; verify all migrations have been applied::

      python manage.py showmigrations | grep "\[ \]"

2. **Tune the application server** — increase the number of gunicorn workers::

      # gunicorn
      --workers $(( 2 * $(nproc) + 1 ))

3. **Enable caching** — configure the Django cache backend in
   ``local_settings.py``. A local Memcached or Redis instance can significantly
   reduce database load::

      CACHES = {
          'default': {
              'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
              'LOCATION': '127.0.0.1:11211',
          }
      }

4. **Archive old data** — if the ``testinstance`` table has millions of rows,
   consider archiving data older than your retention period.

----

.. _high_memory_usage:

High Memory Usage
------------------

**Symptom**

The application server process grows in memory over time and eventually becomes
unresponsive or is killed by the OS.

**Cause**

A memory leak in the application code or a third-party library, or gunicorn
workers are not recycled after processing a large number of requests.

**Solution**

1. Configure gunicorn to recycle workers after a set number of requests::

      --max-requests 1000 --max-requests-jitter 50

2. Monitor memory usage over time with a tool such as ``htop`` or
   ``systemd-cgtop``.

3. If the leak persists, open a
   `GitHub issue <https://github.com/qatrackplus/qatrackplus/issues>`_ with
   the QATrack+ version, Python version, and gunicorn version.

----

.. _slow_reports:

Reports Take Too Long to Generate
-----------------------------------

**Symptom**

Generating a QATrack+ report (PDF or Excel) takes more than a minute or times
out.

**Cause**

The report covers a large date range or many units with many thousands of test
results.

**Solution**

1. Narrow the report date range and limit the number of units or test lists
   included.

2. Schedule the report to run overnight via the built-in scheduled report
   feature instead of generating it on demand.

3. Ensure the database has up-to-date statistics. On PostgreSQL::

      VACUUM ANALYZE;

4. If generation still times out, increase the request timeout in your web
   server configuration. On nginx::

      proxy_read_timeout 300;

**See also**

* :ref:`Reports documentation <reports>`
