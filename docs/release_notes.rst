Release Notes
=============

.. current series release notes will appear in this file,
   older release notes are included from the release_notes directory.
   when incrementing to a new series, the release notes for that series should be added here, and the release notes for the previous series should be moved to the release_notes directory.

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



QATrack+ v3.1
~~~~~~~~~~~~~

.. include:: release_notes/v3.1.rst


QATrack+ v0.3.0
~~~~~~~~~~~~~~~

.. include:: release_notes/v0.3.rst
