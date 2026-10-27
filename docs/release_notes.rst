Release Notes
=============

.. This file holds the notes for the series currently being released, and nothing else.
   Each earlier major series lives in its own file under release_notes/ and is listed in
   the toctree at the bottom - not pulled in with `include`, so each is its own page.

   When starting a new series: move this file's sections into
   release_notes/<series>.rst, give that file a document title at `=` level and a
   `.. _release_notes_series_<n>:` label, add it to the toctree below, and begin the new
   series here.

.. _`release_notes_40`:

QATrack+ 4.0
~~~~~~~~~~~~~

4.0.2
------

Bug Fixes
^^^^^^^^^

* **Forms no longer record the wrong date and time.** Where a date field arrives
  already filled in - the fault form's *Date & Time fault occurred*, a QC session's
  *Work Completed*, a service event's date - the server wrote that value in one format
  and the date picker read it back in another. The picker then replaced it with an
  unrelated date, usually months away and at midnight, before anyone had touched the
  page.

  Nothing indicated it had happened: the replacement was a well-formed date in the
  expected format, sitting in a field the user had not edited. A record saved without
  changing that field carried a time that was simply wrong. Date and time formats are
  now derived from a single setting, so the value written to a form and the value read
  back from it cannot disagree (:issues:`#826 <826>`).

Other Changes
^^^^^^^^^^^^^

* **Dates are now shown as ``YYYY-MM-DD`` by default, in every language.** Two things
  changed, and an upgrading installation will see both.

  **What you will see:** 4.0 rendered ``31 May 2012 14:30`` into form fields; this
  renders ``2012-05-31 14:30``. To keep the old display, set the following in
  ``local_settings.py``:

  .. code-block:: python

      QATRACK_DATETIME_FORMAT = "%d %b %Y %H:%M"
      QATRACK_DATE_FORMAT = "%d %b %Y"

  **What changed for sites with more than one language:** each language used to carry
  its own date format, so the same record read differently depending on the interface
  language the reader had chosen. One format now applies to every language,
  deliberately - a date in a QC record should not change meaning when someone switches
  language - and the setting above moves all of them together. ``%b`` writes English
  month abbreviations in every language; see *Date and Time Format Settings* in the
  configuration documentation.

  Every date format QATrack+ uses is now derived from those two settings, which is what
  makes the fix above possible. The JSON API's format is unchanged.

  .. warning::

      **Breaking, for French and Spanish sites: ``03/05/2026`` is no longer accepted
      when typing a date.**

      4.0.1 gave each language its own list of formats it would *accept*, not just
      display. French accepted ``%d/%m/%Y``, and Spanish had no QATrack+ list at all so
      it fell through to Django's, which accepts it too. Both are gone: every language
      now accepts the display format plus
      ``QATRACK_EXTRA_DATE_INPUT_FORMATS``, which ships as ``%d %b %Y`` only.

      A user typing ``03/05/2026`` gets a validation error rather than a wrong date, so
      nothing is saved incorrectly - but on a French or Spanish site it is a habit that
      stops working. To accept it again:

      .. code-block:: python

          QATRACK_EXTRA_DATE_INPUT_FORMATS = ["%d %b %Y", "%d/%m/%Y"]
          QATRACK_EXTRA_DATETIME_INPUT_FORMATS = ["%d %b %Y %H:%M", "%d/%m/%Y %H:%M"]

      **It is deliberately not shipped as a default, and the reason is worth reading
      before you add it.** ``%d/%m/%Y`` and ``%m/%d/%Y`` cannot be told apart for the
      first twelve days of any month: ``03/05/2026`` is 3 May under one and 5 March
      under the other. Accepting one of them everywhere would silently reinterpret dates
      typed by someone used to the other, and silently is the whole problem this release
      is fixing. Add it where you know which convention your users type in.

Deployment and Upgrade Notes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Docker hosting is supported on Linux only.** QATrack+'s Docker deployment
  needs a Linux server with Docker Engine 23.0 or newer and Docker Compose 2.17 or
  newer. Running it on Windows, including with Docker Desktop, is not supported,
  and the Windows sections of the Docker guide have been removed. On a Windows
  server, use the :ref:`Windows Server installation <win_install_40>`, which
  doesn't use Docker. If your Docker site runs on Windows today, plan a move to a
  Linux server (see :ref:`docker_upgrade_from_4_0`).

* **The Docker installation guide has been reorganised.** :doc:`install/docker` is
  now grouped into setting up, configuring, data and backups, running QATrack+ day
  to day, and development, and its out-of-date parts are fixed: the Django shell
  is ``docker compose exec django python manage.py shell``, removing a site is
  explained safely (``docker compose down -v`` deletes the database, uploaded files
  and generated secret key), and the nightly backup is shown at the time it really
  runs, which is now 4 AM in QATrack+'s own time zone (see below). Thanks to
  Vincent Leduc, whose reorganisation of the Docker docs in :issues:`#866 <866>`
  this draws on.

* **Docker: Docker Compose 2.17 and Docker Engine 23.0 are now the minimum. Check
  before you pull.** With an older Compose, the commands that build or create
  containers (``up``, ``build``, ``run`` and others) stop with *Additional property
  additional_contexts is not allowed*. Running containers keep running, but 4.0.2
  can't be built or started, and containers removed with ``docker compose down``
  can't be created again, until Docker is updated. See
  :ref:`docker_upgrade_check_compose`.

* **Docker: ``deploy/docker/.env`` is no longer tracked by git. Set your copy aside
  before you pull.** It holds the database password, so it no longer belongs in the
  repository. Every Docker site has edited it, so on the first pull to 4.0.2
  ``git pull`` stops with *Your local changes would be overwritten*. Follow
  :ref:`the steps in the Docker upgrade guide <docker_upgrade_env_untracked>`: copy
  ``.env`` aside, pull, and copy it back. Later pulls leave it alone. New
  installations create it with ``cp .env.example .env``.

* **Docker sites can now set QATrack+'s settings in ``deploy/docker/.env``.**
  Previously only the database credentials, ``ALLOWED_HOSTS`` and
  ``CSRF_TRUSTED_ORIGINS`` could be set, and everything else needed a change inside
  the image. ``deploy/docker/.env.example`` now documents every setting available:
  email, time zone, HTTPS behind the proxy, sessions, the QC display options,
  accounts, ADFS, Active Directory / LDAP sign-in (including username cleaning), and
  the REST API. The Docker image now includes ``python-ldap``, so LDAP sign-in works
  there too.

  ``localhost`` and ``127.0.0.1`` are always allowed hosts, so the container health
  check keeps working when ``ALLOWED_HOSTS`` names only the real host. They are
  never trusted CSRF origins.

* **Docker: the secret key now lives in a volume, or in ``.env``.** When
  ``SECRET_KEY`` is not set, QATrack+ generates one and keeps it in the
  ``user-data-volume`` volume, so rebuilds never sign users out. 4.0.0 and 4.0.1
  kept the key in your QATrack+ folder (``deploy/docker/user-data/secret_key.txt``),
  so a new one is generated on the first start of 4.0.2, signing every user out once
  and voiding password-reset links sent before the upgrade. To avoid that, copy the
  old key into ``.env`` first (see :ref:`docker_upgrade_keep_secret_key`).

* **Docker: QATrack+ says where it keeps the secret key it generated.** When
  ``SECRET_KEY`` is not set in ``.env``, each start of the ``django`` service
  logs a short notice naming the key file. The nightly backup does not include
  it, so the notice and :ref:`docker_secret_key` show how to copy the key into
  ``.env``, where losing the volume can no longer sign everyone out.

* **Docker: the upgrade keeps your other local changes.** If you changed the port
  in ``compose.yaml`` or edited ``nginx.conf``, the upgrade guide's ``git stash``
  steps keep those changes across ``git pull``.

* **Docker: scheduled notifications and reports now run.** Docker installations
  had no process running QATrack+'s background tasks, so scheduled QC
  notifications, scheduled reports and the emails they send were never sent. A
  new ``django-q`` service runs them; it starts with the next
  ``docker compose up -d``.

* **Docker: HTTPS works.** nginx published port 443 but had no HTTPS
  configuration. With ``HTTP_OR_HTTPS=https`` in ``.env`` and your certificate
  and key in ``deploy/docker/user-data/ssl``, nginx now serves QATrack+ over
  HTTPS, redirects HTTP to it, and tells QATrack+ the request was secure (see
  :ref:`docker_https`).

* **Docker: a database client can connect to PostgreSQL, if you turn it on.** The
  database is still not published on the server unless you ask, so an upgrade
  opens no new port. Listing the new ``compose.db-port.yaml`` in ``COMPOSE_FILE``
  in ``.env`` publishes it on ``127.0.0.1``, port 5434 (``POSTGRES_HOST_PORT``
  changes it), for a client or reporting tool on the server, or for one elsewhere
  through an SSH tunnel. See :ref:`docker_postgres_access`. Thanks to Vincent
  Leduc, whose pull request this is based on (:issues:`#866 <866>`).

* **Docker: nginx answers only the hosts in ``ALLOWED_HOSTS``.** Requests for any
  other host name are dropped before they reach QATrack+, so they no longer
  produce *Invalid HTTP_HOST header* errors (and error emails to ``ADMINS``).
  ``ALLOWED_HOSTS=*`` keeps passing every host on.

* **Docker: uploads larger than 1 MB work.** nginx used its 1 MB default limit,
  which rejected larger uploaded test results and attachments. The limit is now
  100 MB, set with ``NGINX_CLIENT_MAX_BODY_SIZE``.

* **Docker: the site no longer answers 502 after an upgrade.** nginx looked up the
  ``django`` service's address once, when it started. An upgrade that recreated
  ``django`` could give it a new address, and nginx kept sending requests to the
  old one until it was restarted. It now looks the address up as requests arrive.

* **Docker: a slow first start no longer leaves the site down.** ``django`` runs
  every database migration before it reports that it is ready. On slow storage
  that took longer than Docker allowed, so ``docker compose up`` gave up and never
  started nginx. ``django`` now has up to 10 minutes.

* **Docker: links in emails and reports point to your site.** Django's site
  record starts as ``example.com``, and QATrack+ builds the links in its emails and
  reports from it, so on Docker they pointed to ``http://example.com/...`` unless an
  administrator changed the record. Now that scheduled emails are sent, QATrack+
  fills the record in on start: from ``SITE_DOMAIN`` and ``SITE_NAME`` in ``.env``
  if set (every start), otherwise once from the first host name in
  ``ALLOWED_HOSTS`` while the record is still ``example.com``. A domain and name
  you have already set in the admin are kept, unless ``SITE_DOMAIN`` or
  ``SITE_NAME`` is set in ``.env``: those replace them on every start. So if you
  manage them in the admin, leave both commented out when you compare your
  ``.env`` with ``.env.example``. ``SITE_NAME`` sets the name shown at the top of
  each page.

* **Docker: backups can be restored, and an interrupted backup can't pass for a
  finished one.** The ``backup`` service now writes each file under a temporary
  name, reads it back in full, and renames it only once it is complete. It
  refuses to start while another backup or a restore is running. Backups are
  now readable only by root on the server, and the first backup after the
  upgrade does the same to older ones, so copy them with ``sudo``. Two new
  commands, ``restore-db`` and ``restore-media``, put a backup back after checking
  it and asking you to confirm (see :ref:`docker_backups`). They unpack the
  backup beside your current data and only then swap it in, so a restore that
  fails or is stopped leaves your data as it was; while one runs, the disk needs
  room for that second copy. The ``backup`` service can still only read the
  uploaded files; ``restore-media`` runs as its own service, which can write to
  them, and only when you ask for it. Backups made by QATrack+ 4.0.0 and 4.0.1
  can be restored. The backup service's PostgreSQL tools are now pinned to
  version 16, the version that made those backups: PostgreSQL 15's tools cannot
  read them. The image now installs just those client tools on Alpine, rather
  than starting from the PostgreSQL server image.

* **Docker: the nightly backup moves to 4 AM local time.** It ran at 2 AM UTC,
  which is the evening before across the Americas (10 PM in Toronto in summer),
  and named its files in UTC. It now runs at 4 AM in QATrack+'s own time zone,
  ``TIME_ZONE`` in ``.env``, and names its files in that local time. If
  ``TIME_ZONE`` is not set, that is QATrack+'s default, America/Toronto, which
  QATrack+ already shows dates in: set it if your site is elsewhere.
  ``docker compose logs backup`` shows the zone in use. 4 AM rather than 2 AM
  because no time zone changes its clocks for daylight saving time at 4 AM, so the
  backup runs once every night, all year round (see :ref:`docker_backups`).
  Backups from before the upgrade keep their UTC names, so for a day or so the
  names do not sort in the order the backups were made; ``ls -lt`` lists them
  newest first. The first backup after the upgrade may come up to a day sooner or
  later than usual. **If a job copies the backups off the server** at a time
  chosen to follow the old 2 AM UTC backup, move it to after 4 AM local time, or
  it will copy the previous night's backup.

* **Docker: QATrack+'s data can be kept in folders on the server.** Nothing changes
  unless you ask for it: the uploaded files, log files and generated secret key stay
  in their Docker volumes, and the backups in ``deploy/docker/backups``. To keep any
  of them in a folder you already back up or watch, set ``QATRACK_MEDIA_DIR``,
  ``QATRACK_LOGS_DIR``, ``QATRACK_USER_DATA_DIR`` or ``QATRACK_BACKUPS_DIR`` in
  ``.env``. Every service, the nightly backup and ``restore-media`` included, uses
  the same folder, and the ``init`` service gives the folder to the QATrack+ user
  each time the site starts. So that it never does this to anyone else's files,
  ``init`` only uses a folder that is empty (which it marks with a
  ``.qatrackplus-data`` file) or already marked, that is not inside another of
  QATrack+'s folders, and that holds neither another of them nor a backup;
  otherwise the site does not start, nothing is changed, and
  ``docker compose logs init`` says why. A file with a second name (a hard link)
  is never handed over. For a site already in use, copy the data
  across first: :ref:`docker_data_dirs` shows how, step by step. The database stays
  in its volume. ``init`` also no longer follows symbolic links or crosses into
  another disk when it re-owns files, so a link can neither change a file outside
  QATrack+'s folders nor, if it points nowhere, stop the site from starting, and it
  logs how many files it re-owned. Based on the ``/app_data`` layout proposed
  in :issues:`#866 <866>`.

* **Docker: container output is capped** at 50 MB per service, so what
  ``docker compose logs`` keeps can no longer fill the disk. That output belongs to
  each container and starts again empty when the container is recreated, for
  example by an upgrade. Every service now has a health check, shown by
  ``docker compose ps``.

* **QATrack+'s log files now rotate.** ``debug.log``, ``auth.log``, ``migrate.log``
  and ``django-q2.log`` were set up to rotate but never did, so they grew without
  limit. Each now starts a new file at 10 MB and keeps a fixed number of old ones.
  This applies to every installation, not only Docker.

* **Background tasks can run for up to 5 minutes**, up from 1. A scheduled report
  whose PDF took longer than a minute to make was stopped and never sent. This
  applies to every installation.

* **Docker: overdue follow-up emails are sent when background tasks first run.**
  Follow-up emails from *QC Completed* notices were queued but never sent on
  Docker, and 4.0.2 sends every one still waiting as soon as it starts. To remove
  them first, see :ref:`docker_upgrade_stale_follow_ups`.

* **The Docker application container no longer runs as root.** QATrack+ now runs as
  an unprivileged ``qatrack`` user (uid 1000). Calculation procedures for composite
  and upload tests run inside the application, with its privileges, so on earlier
  releases they ran as root inside the container. They still run with the
  application's privileges: they can read its environment, including the database
  password, and use the database. But they can no longer change QATrack+'s own code
  or the container's system files.

  Nothing changes in the commands you run. Existing media and static files, written
  as root by earlier releases, are re-owned automatically the next time you run
  ``docker compose up -d``; on a large media volume that first start takes longer.
  A short-lived ``init`` container that does this appears as exited in
  ``docker compose ps -a``, which is expected.

* **Docker: ``compose.override.yaml`` is now ``compose.dev.yaml`` and is no longer
  applied automatically.** The override mounted the whole checkout over the code in
  the image, so every plain ``docker compose`` command ran the checkout instead of
  the image, as root. Plain ``docker compose`` now runs the code built into the
  image. Developers who want their checkout live use
  ``docker compose -f compose.yaml -f compose.dev.yaml``, with their own ids in
  ``.env`` (see :ref:`docker_development`).

  QATrack+'s log files are now kept in a ``logs-volume`` volume, shared by the
  ``django`` and ``django-q`` services, rather than in the checkout's ``logs``
  folder, and they survive upgrades. Read them with
  ``docker compose exec django ls logs`` and
  ``docker compose exec django tail -n 50 logs/debug.log``. With the development
  overlay they are still written to your checkout's ``logs`` folder.

* **The Docker image installs exactly the dependency versions in ``uv.lock``**, the
  same versions the test suite runs against. Previously ``pip`` chose versions when
  the image was built, so two builds of the same release could differ.

* **Docker: add your own Python packages for calculation procedures.** List them in
  ``deploy/docker/site-requirements/requirements.txt`` and run
  ``docker compose build``. They are installed at versions that work with
  QATrack+'s own, and a package that needs a different version of one of them
  stops the build instead of changing what QATrack+ runs on. Wheel files in the
  same folder can be installed without internet access. See
  :ref:`docker_site_packages`.

* **Docker images no longer contain your ``.env`` file, local settings or site data.**
  The ``.dockerignore`` patterns only matched files at the top of the repository, so
  the image copied in ``deploy/docker/.env`` (which holds the database password), and
  anything else present in the checkout when it was built: a generated
  ``deploy/docker/user-data/secret_key.txt``, database dumps under
  ``deploy/docker/backups/``, uploaded files under ``qatrack/media/uploads/`` and
  ``qatrack/local_*.py`` settings files. The image now receives only the files it
  needs to run. If you have copied a QATrack+ image to a registry or another machine,
  rebuild it with ``docker compose build`` and remove the old one.

* **Database dumps written by the Docker backup service are ignored by git.**
  ``deploy/docker/backups/`` was not in ``.gitignore``, so ``git status`` listed every
  nightly dump and ``git add -A`` would have committed them. Environment files
  (``.env``, ``*.env``, ``.env.*``) are now ignored as well, except the
  ``.env.example`` templates, including ``deploy/docker/.env`` (see above).

* **Files under ``deploy/docker`` always check out with LF line endings**, whatever
  git's ``core.autocrlf`` setting. A Dockerfile or script with CRLF endings fails
  inside the container. A checkout made on Windows and copied to a Linux server
  keeps its current line endings until the files are checked out again; see
  :ref:`checking out deploy/docker again <docker_line_endings>`.

4.0.1
------

Bug Fixes
^^^^^^^^^

Ordered by consequence, most serious first.

* **``manage.py backup_site`` says when it has not backed up the database.** On MySQL,
  and on any engine it does not implement, it skipped the database without a word and
  finished as though it had written one, so a site could hold a set of backups
  containing no database at all. It now names the engine it cannot handle and skips
  the retention step rather than passing silently.

  **It still exits zero.** The command has no non-zero exit path, so a cron job or
  script that checks only the exit status cannot tell a complete backup from one with
  no database in it. Read its output, or check that a database file is present.
  Making it fail properly changes behaviour for anything already scheduled around
  it, so that is not in this patch release.

  It writes a database backup on **SQL Server and SQLite** only. PostgreSQL has never
  been among them - the command has always said so rather than failing quietly - so
  nothing changes for a PostgreSQL site, but one relying on this command does not
  have a database backup. Use ``pg_dump``, or the Docker backup script. There is an
  appendix in :ref:`qatrack_backup` for sites running SQLite in production.

* **PDF reports are complete again.** A report containing a forced page break
  silently lost everything after it, which affected the service log and fault
  reports, paper QC backup forms and test list instance details. The on-screen
  preview was unaffected, so the download appeared to be at fault rather than the
  report itself.

* **Service areas show their own names.** Every service area rendered as the words
  "service area" - in the admin, in every dropdown listing them, and anywhere a
  template showed one - so with more than one configured there was no way to tell
  them apart on screen.

* **The "Due & Overdue QC" page includes everything due today.** Its cutoff was
  midnight at the start of the day rather than the end of it, so an item that came
  due this morning did not appear until tomorrow, on the one page whose purpose is to
  show what is due. The Due Dates report was never affected and has always used the
  end of the day; the page now matches it.

* **Scheduled service event notices are sent again.** The periodic task was
  registered under a function name that does not exist, so it could never run
  (:issues:`#852 <852>`).

* **Report schedules can be created again.** Opening the schedule dialog for a report
  raised an ``AttributeError`` from ``ReportSchedule.__str__``, which read an
  ``rrule`` attribute that does not exist, so the schedule could not be saved. The
  translation catalogue is also loaded on the reports and charts pages, which
  previously fell back to untranslated strings (:issues:`#837 <837>`).

* **Report links no longer double the URL scheme.** A Site domain is documented as a
  bare host, but setting it to a full URL such as ``https://example.com`` is common,
  and the links in report bodies and the "View on site" header prepended the scheme a
  second time - producing ``http://https://example.com/...``, which a browser reads
  as the host ``https`` with the real host pushed into the path. Every such link was
  broken (:issues:`#853 <853>`).

* **Service event templates match return-to-service QC by intersection.** A template
  was excluded from a unit whenever it named any test list the unit was not assigned,
  rather than offering the ones it was, so a template could not be shared across
  machines or modalities (:issues:`#829 <829>`).

* **A fault type whose code has no ASCII form works.** Such a code produced an empty
  identifier, and its pages returned a 500 (:issues:`#677 <677>`).

* **String and string composite tests can be given a multiple choice tolerance
  again** (:issues:`#881 <881>`).

* **Composite and constant calculation procedures may use any Python the site runs
  on.** Procedures were checked against a syntax target fixed at Python 3.6 to 3.9,
  so ``match`` statements and ``type`` aliases were rejected on a site running 3.12.

* **Report PDFs load their stylesheets and logo on Windows.** Links were built by
  joining ``file://`` to a filesystem path, which on Windows turns the drive letter
  into a hostname, so none of a report's nine stylesheet and image links resolved and
  the PDF rendered unstyled and without the organisation logo.

* **Reports honour their paper size when a browser renders them.** A report set to A4
  was produced at Letter regardless.

* **The organisation logo sits in the top right of a report** rather than wrapping
  onto a second line below the heading.

* **A report's signature and date fields stay on one line** on A4 paper.

* **Report generation no longer leaves a partial PDF behind** when the browser fails
  part way through.

* **The schedule rule is readable in the report scheduling dialog** in dark mode,
  where it was white on white (:issues:`#837 <837>`).

* **Table controls on listing pages are translated.** *Showing x of y*, *Previous*,
  *Next*, *Search:* and *No data available* always rendered in English whatever
  language was active, because the tables' translated strings were never passed to
  DataTables (:issues:`#827 <827>`).

* **Client-side translations reach users who are not logged in.** The JavaScript
  translation catalogue was not exempt from the login requirement, so an anonymous
  visitor's request redirected to the login page, the browser parsed the HTML as
  JavaScript, and no client-side string was translated.

* **An intermittent JavaScript error on the QC overview, the parts reporting page and
  the unit available time page is gone.** Each used a scrollbar plugin without
  declaring it as a dependency, so whether it had loaded in time depended on what
  else a page happened to pull in first (:issues:`#822 <822>`).

Other Changes
^^^^^^^^^^^^^

* **Three ``Makefile`` targets that emptied application data have been removed:**
  ``clearct``, ``flushdb`` and ``__cleardb__``. Each acted on the database named by
  ``local_settings.py``, which in a clinical installation is the live one. Two were
  already broken and would have failed before doing damage; ``clearct`` worked. None
  is needed for any documented workflow, and ``make help`` advertised all three
  alongside the ordinary targets.

* **A sample data generator for development and debugging.**
  ``manage.py generate_sample_data`` builds a small site's worth of units, test lists
  and QC history, so a developer can reproduce behaviour that needs populated data
  without a copy of anyone's database.

* **The language a user selects persists.** The language cookie had no explicit
  lifetime, so it expired with the browser session and the interface reverted to the
  default language on the next visit.

Deployment and Upgrade Notes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Python 3.12 and Django 4.2.30 or newer are now required.** The Django floor was
  raised to pick up its security fixes, and Python is pinned to 3.12 - the version
  QATrack+ 4.0 is tested and deployed on.

* **The Docker backup script reads its database settings from the environment.**
  ``deploy/docker/backup/backup.sh`` previously hard-coded the database name and
  user. It now uses ``POSTGRES_DB``, ``POSTGRES_USER`` and ``POSTGRES_PASSWORD``, so a
  deployment that sets those in its Compose environment is backed up correctly, and
  one that does not will fail rather than dump the wrong database. Check your
  ``.env`` before relying on the next backup.

* **``CSRF_TRUSTED_ORIGINS`` can be set from the environment** for Docker
  deployments, falling back to ``ALLOWED_HOSTS`` when it is not given. See the notes
  in ``deploy/docker/.env.example``.

* **The ``installfixtures`` management command has been removed.** It loaded a
  fixture set that no longer matched the schema. Use ``manage.py loaddata`` with the
  fixtures you want.

* **The Windows upgrade guide has its service-setup section back** - the steps that
  register the QATrack+ service - which had gone missing.

4.0.0
------

QATrack+ 4.0.0 introduces a major platform modernization release focused on maintainability, deployment consistency, and long-term support readiness. This release includes updates to the Python and Django stack, Windows deployment tooling, and admin architecture.

Highlights
^^^^^^^^^^

* Localization support for multiple languages. Draft translations are available for English, French, and Spanish. 
* Upgraded core platform to newer Python and Django ecosystem components.
* Standardized environment and dependency management around uv.
* Improved Windows deployment workflow for both fresh installs and upgrades.
* Updated SQL Server guidance and local settings expectations for modern Django behavior.

Major Changes
^^^^^^^^^^^^^

* Windows deployment documentation has been refreshed for Server 2022 and SQL Server 2022 scenarios.
* Dependency and environment management now uses uv workflows for setup and synchronization.
* Windows service deployment is now fully automated via `install_winsw.ps1`, adopting a centralized WinSW wrapper (`qatrack-service.exe`) and simplifying the service name to `QATrack+ Web Service`.
* Local settings expectations now explicitly include host and CSRF origin configuration required by current Django versions.
* Database engine guidance for SQL Server has been updated to current backend conventions.

Technical Improvements
^^^^^^^^^^^^^^^^^^^^^^

* Removed external django-admin-views dependency and migrated related functionality into Django admin.
* Consolidated and simplified admin URL and view handling.
* Reduced package complexity by removing an unnecessary external dependency from the stack.
* Improved consistency of installation and upgrade command sequences.
* Updated time handling to use timezone-aware datetimes throughout the codebase.
* Added a `generate_sample_data` management command for development and testing. It fills a database with a small radiation oncology centre: two linacs and a CT simulator, TG-142 style daily and monthly QA protocols with references and tolerances, rolling QA history including an unreviewed backlog, service events with return to service QA, faults, a parts inventory, and saved reports with schedules. Re-running it extends the data rather than duplicating it, and the `--clear` option (which empties those tables for the whole database) asks for confirmation first. See the developers guide for the command's options and the sample logins.
* The development local settings template now enables `DEBUG` and sets `ALLOWED_HOSTS` for local addresses, and default fixture loading no longer depends on the current working directory.

Bug Fixes
^^^^^^^^^

* Service Event Templates can now be shared across different machines and modalities. When selecting a template, only the Return to Service tests that apply to the chosen unit will be added to the form (:issues:`#829 <829>`).
* Fixed an issue where resuming an autosaved QC session could display the wrong start date and time.
* Fixed tolerance compatibility validation across different test types.
* Fixed reference value type preservation in admin forms.
* Improved handling and messaging for incompatible tolerance and test-type combinations.
* Addressed multiple documentation inconsistencies and deployment workflow ambiguities.

Deployment and Upgrade Notes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Existing Windows v3.1 installations should follow the dedicated 4.0 upgrade guide.
* New installations should use the fresh install guide for uv-based environment setup.
* Verify service and task definitions after upgrade to ensure they point to the active virtual environment Python executable.
* Review local settings before first startup, including host and CSRF origin settings.

Acknowledgements
^^^^^^^^^^^^^^^^

Thank you to everyone who contributed bug reports, validation feedback, deployment testing, and documentation improvements that helped shape this release.

Contributors from the project history include:

* Cody Crewson (`@crcrewso <https://github.com/crcrewso>`_)
* Nathan Smela (`@NSmela <https://github.com/NSmela>`_)
* Ethan Sutherland (`@ETS1199 <https://github.com/ETS1199>`_)
* Matt Van Horn (`@mvanhorn <https://github.com/mvanhorn>`_)
* Vincent Leduc (`@leducvin <https://github.com/leducvin>`_)
* trugty (`@trugty <https://github.com/trugty>`_)



Earlier Series
~~~~~~~~~~~~~~

The notes for each earlier major series are kept as their own page rather than being
pulled into this one, so that this file only ever holds the series currently being
released.

.. toctree::
   :maxdepth: 1

   release_notes/v3.1
   release_notes/v0.3
   release_notes/v0.2
