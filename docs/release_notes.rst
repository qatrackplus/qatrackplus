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

QATrack+ v4.0
~~~~~~~~~~~~~

v4.0.1
------

Bug Fixes
^^^^^^^^^

* Fixed PDF reports being truncated part way through. Any report containing a
  forced page break silently lost everything after it, which affected the
  service log and fault reports, paper QC backup forms, and test list instance
  details. The on screen preview was unaffected, so the download appeared to be
  at fault rather than the report itself.
* Fixed the organisation logo wrapping onto a second line below the report
  heading instead of sitting in the top right corner.
* Fixed the signature and date fields being placed on different lines when a
  report is generated on A4 paper.
* Fixed the report paper size being ignored when PDFs are generated with
  Chrome. Reports set to A4 were produced at Letter size regardless of the
  paper size chosen for the report.
* Service areas show their own names again. Every service area rendered as the
  words "service area" - in the admin, in every dropdown listing them, and
  anywhere a template showed one - so with more than one configured there was no
  way to tell them apart on screen.
* Report PDFs generated without a browser load their stylesheets and logo
  again on Windows. The links were built by joining ``file://`` to a filesystem
  path, which on Windows turns the drive letter into a hostname, so none of the
  nine stylesheet and image links in a report resolved and the PDF rendered
  unstyled and without the organisation logo.
* Report generation no longer leaves a partial PDF behind when the browser
  fails, and a failure now says whether the browser could not be run or ran and
  produced nothing, rather than reporting both as a missing executable
  (:issues:`#835 <835>`).
* Scheduled service event notices are sent again. The periodic task was
  registered under a function name that does not exist, so it failed roughly
  every 15 minutes and no notices went out. The failure appeared only in the
  Django Q cluster log, never in QATrack+ itself (:issues:`#852 <852>`).
* Fixed the schedule rule being invisible in the report scheduling dialog for
  anyone whose operating system or browser is set to a dark colour scheme. The
  rule's text was rendered white on the dialog's white background, so the
  Schedule box appeared to be empty apart from its close button, whether the
  report already had a schedule or a rule had just been added. Users with a
  light colour scheme were never affected, which is why it appeared to happen
  "without any changes made on the server" (:issues:`#837 <837>`).

* Composite and constant test calculation procedures may now use any Python
  syntax the server runs. Procedures containing a ``match`` statement or a
  ``type`` alias were refused on save with *Calculation procedure invalid:
  Cannot parse for target version Python 3.9*, although QATrack+ requires
  Python 3.12.
* String and string composite tests can be given a multiple choice tolerance
  again. Since v4.0.0 the reference and tolerance admin offered only absolute
  and percentage tolerances for them, so a test upgraded from v3.1 that returned
  values such as ``PASS`` or ``Incorrect Linac`` could not be assigned the
  tolerance it had been using. Wraparound tests are again restricted to absolute
  tolerances (:issues:`#881 <881>`).
* Fixed fault types whose code produces no usable URL identifier being unusable.
  The identifier is derived by reducing the code to plain ASCII, and a code that
  leaves nothing behind was given an empty one - so the fault type's own page
  returned a server error and the "All Fault Types" table stopped at
  "Processing..." with no rows and no message. A second such code fared little
  better, receiving the meaningless address "1". This affects any script with no
  ASCII form, such as Chinese, Cyrillic, Greek or Arabic, and also a handful of
  Latin letters that are not accented forms of an ASCII letter - ``Ø``, ``Ł``,
  ``Đ``, ``Œ``, ``Æ`` and ``ß`` among them. Codes that already produced a
  non-empty ASCII identifier, such as ``Arrêt``, were never affected. **A fault
  type already carrying an empty identifier is repaired by opening it in the
  admin and saving it**, which regenerates the identifier; addresses that already
  worked are left unchanged
  (:issues:`#677 <677>`).

* Fixed the "Due & Overdue QC" page leaving out everything due later the same
  day. The cutoff was midnight at the start of today rather than the end of it,
  so an item that came due this morning did not appear until the following day,
  on the one page whose purpose is to show what is due. The Due Dates report was
  never affected and has always used the end of the day; the page now matches it.

* Scheduled report notices can be defined again. Opening the schedule dialog for a
  report raised an ``AttributeError`` from ``ReportSchedule.__str__``, which read an
  ``rrule`` attribute that does not exist, so the schedule could not be saved. The
  translation catalogue is also loaded on the reports and charts pages, which
  previously fell back to untranslated strings (:issues:`#837 <837>`).
* Report links no longer double the URL scheme. A Site domain is documented as a bare
  host, but setting it to a full URL such as ``https://example.com`` is common, and the
  links in report bodies and the "View on site" header prepended the scheme a second
  time - producing ``http://https://example.com/...``, which a browser reads as the host
  ``https`` with the real host pushed into the path. Every such link was broken.
* The table controls on listing pages are translated again. *Showing x of y*,
  *Previous*, *Next*, *Search:* and *No data available* always rendered in English
  whatever language was active, because the tables' translated strings were never
  passed to DataTables (:issues:`#827 <827>`).
* Client-side translations work for users who are not logged in. The JavaScript
  translation catalogue was not exempt from the login requirement, so for anonymous
  visitors the request redirected to the login page, the browser parsed the HTML as
  JavaScript, and no client-side string was ever translated.
* Fixed an intermittent JavaScript error on the QC overview, the parts reporting page
  and the unit available time page. Each used a scrollbar plugin without declaring it
  as a dependency, so whether it had loaded in time depended on what else a page
  happened to pull in first.
* ``backup_site`` no longer reports success when it has not backed up the database.
  On MySQL, and on any engine other than PostgreSQL and SQLite, it skipped the database
  silently and still finished as though it had written one - so a site could hold a set
  of backups containing no database at all. It now says which engine it cannot handle
  and fails that step.

Other Changes
^^^^^^^^^^^^^

* **Three ``Makefile`` targets that emptied application data have been
  removed:** ``clearct``, ``flushdb`` and ``__cleardb__``. Each acted on
  whichever database ``local_settings.py`` configured - which, in an
  installation made by ``git clone``, is the live one - and ``__cleardb__``
  deleted every test list instance, meaning the QC history. Two of the three
  never worked at all. Nothing in QATrack+ referenced any of them. Use
  ``python manage.py flush`` if you need Django's own equivalent.

  While in the file, two dead targets went with them - ``yapf`` and ``flake8``,
  neither installed nor declared as a dependency since ruff replaced both - and
  ``make help`` was added, listing the targets that are safe to use. The
  developer guide had described ``make help`` for some time without the target
  existing, so the command silently did nothing; a bare ``make`` now prints it
  as well.

* The language a user selects now persists. The language cookie had no explicit
  lifetime, so it expired with the browser session and the interface reverted to the
  default language on the next visit.

Deployment and Upgrade Notes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Python 3.12 and Django 4.2.30 or newer are now required.** The Django floor was
  raised to pick up its security fixes, and Python is pinned to 3.12 - the version
  QATrack+ 4.0 is tested and deployed on.
* **The Docker backup script now reads its database settings from the environment.**
  ``deploy/docker/backup/backup.sh`` previously hard-coded the database name and user.
  It now uses ``POSTGRES_DB``, ``POSTGRES_USER`` and ``POSTGRES_PASSWORD``, so a
  deployment that sets those in its Compose environment is backed up correctly, and one
  that does not set them will fail rather than dump the wrong database. Check your
  ``.env`` before relying on the next backup.
* **``CSRF_TRUSTED_ORIGINS`` can be set from the environment** for Docker deployments,
  falling back to ``ALLOWED_HOSTS`` when it is not given. See the notes in
  ``deploy/docker/.env.example``.
* **The ``installfixtures`` management command has been removed.** It loaded a fixture
  set that no longer matched the schema. Use ``manage.py loaddata`` with the fixtures
  you want.

v4.0.0
------

QATrack+ v4.0.0 introduces a major platform modernization release focused on maintainability, deployment consistency, and long-term support readiness. This release includes updates to the Python and Django stack, Windows deployment tooling, and admin architecture.

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

* Existing Windows v3.1 installations should follow the dedicated v4.0 upgrade guide.
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
