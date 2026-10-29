Tell QATrack+ its own name and address
--------------------------------------

**Do this once, after the first start.** Until you do, QATrack+ calls itself
``example.com``:

* every browser tab reads **example.com: Log In**, and so does the name in the page
  header;
* the links in emailed notifications and scheduled reports point at
  ``http://example.com/...``, so nobody who receives one can click through to your
  server.

Nothing is broken and no data is at risk - QATrack+ simply has not been told what it
is called.

Where the value lives
~~~~~~~~~~~~~~~~~~~~~

It is a **row in the database**, not a line in a settings file. Django keeps a small
table of one row holding two fields, and QATrack+ reads both from there:

* **Domain name** - the host name people type to reach QATrack+, for example
  ``qatrack.myclinic.ca``. The emailed links are built from this.
* **Display name** - the words shown in the browser tab and the page header, for
  example ``QATrack+`` or ``Medical Physics QC``.

The row ships as ``example.com`` for both, because that is Django's default and the
software cannot know your host name.

.. warning::

    **There is a ``SITE_NAME`` setting, and on a native install changing it does
    nothing.** It exists in
    ``qatrack/settings.py``, and on Docker it can be set in ``.env`` - but QATrack+
    reads the name from the database row, so the setting is ignored. Only the row
    matters. If you have already set ``SITE_NAME`` and seen no change, this is why.

.. note::

    **Two different things in the admin are called "Sites".** They are unrelated:

    * **Sites** on its own, with exactly one row and the fields *Domain name* and
      *Display name* - this is the one on this page.
    * **Sites** under **Units**, where you group treatment units by physical location.
      That is a QATrack+ feature for your own clinic layout and has nothing to do with
      the name of the website.

Setting it
~~~~~~~~~~

In the admin, open **Sites**, click the single ``example.com`` row, and set both
fields. Or from a terminal:

.. code-block:: bash

    python manage.py shell -c "
    from django.contrib.sites.models import Site
    s = Site.objects.get_current()
    s.domain = 'qatrack.myclinic.ca'; s.name = 'QATrack+'; s.save()"

On Docker, run that inside the container:

.. code-block:: bash

    docker compose exec django python manage.py shell -c "
    from django.contrib.sites.models import Site
    s = Site.objects.get_current()
    s.domain = 'qatrack.myclinic.ca'; s.name = 'QATrack+'; s.save()"

Then restart the application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Changing the row is not enough on its own.** Django reads it once per process and
keeps it, so a running server goes on serving the old value and the change looks as
though it did nothing:

.. list-table::
    :header-rows: 1

    * - Installation
      - Restart
    * - Ubuntu Linux
      - ``sudo supervisorctl restart gunicorn django-q2``
    * - Windows Server
      - restart the **QATrack+ Web Service** in the Windows Services dialog
    * - Docker
      - ``docker compose restart django django-q``

Reload the login page afterwards; the tab should now read your display name.

.. note::

    **If you ever rebuild the database from the default fixtures, the row goes back to
    ``example.com``.** Re-apply it after any rebuild. Upgrading does not touch it.
