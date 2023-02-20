Release Notes
=============

QATrack+ v3.2.0 Release Notes
-----------------------------

* Site has now been made a mandatory field on Units. This simplifies code in
  places as it doesn't require developers to add extra logic for handling null
  site fields. Any existing units without a Site assigned to it will
  automatically be assigned to an "Default" site.

* Unit Class has now been made a mandatory field on Unit Types.  Any existing
  unit types without a unit class assigned to it will automatically be assigned
  a "Default" unit class.

* Room & Storage models have been moved from the Parts app to the Units app.

* Fixed bug where saving reports in the admin would result in invalid JSON
  being stored for the filters.

* Fixed API bug where default calculations were not being considered when
  posting test list instance data

* Added default reference & tolerance fields to the Test model. This 
  can greatly reduce the amount of work to configure references & tolerances
  when assigning the same tests to many units.

* Moved the review status from being test instance level to test list instance
  level.  This simplfies the reviewing of test list instances conceptually and
  from a UI perspective. There were also some query performance benefits.

* Fixed missing set_value check for WrapAround tests which caused AutoSave to
  not load for Wrap Around tests.

* Fixed correct setting of skips after composite calculations

* Added new `AD_DISABLE_STRICT_CERT_CHECKING` to allow self signed certificates
  to be used with Active Directory

* Fixed a bug when trying to send reports to groups with no members

* Fixed fault list review status ordering/searching bug

* Deleting a unit will now cascade and delete UnitTestInfo & UnitTest objects.
  Existing QA data will still prevent a Unit from being deleted.


QATrack+ v3.1.1 Release Notes
-----------------------------

.. _release_notes_311:


This is a follow up release to address a few issues that were found in v3.1.0. The following
issues have been addressed:

QA
~~

* Added basic multiple choice plotting support
* Fixed a Test admin bug with the display of "Test item visible in charts"
* A message warning you about being logged out or your server not being
  reachable will be shown after 3 consecutive unauthenticated or failed
  pings.  In order to disable this check set `PING_INTERVAL_S = 0` in your
  local_settings.py file.
* The maximum frequency of autosaves has been reduced to once per 4s. This an attempt
  to work around occasional deadlocks with SQL Server.
* Pylinac has been updated (TODO: version):
    * An issue with CatPhan modules CNR calculations return NaN due to the modules not having
      background ROIs defined has been fixed
    * A bug with DMLC VMAT tests with valleys in their profiles that fell below 50% of Dmax has
      been fixed.
    * A regression in QC3 image detection introduced in the QATrack fork of Pylinac has been
      remedied.
* A bug with QA Frequency recurrence rule start dates has been fixed
* The Assign Test Lists to Units admin page will no longer allow a blank Assigned to Field
* Sometimes a test which was skipped by default would not get unskipped when a user
  performed the test.  This has been resolved.

* The confirmation dialogue for reviewing QA was not showing the status
  correctly.  This has now been resolved.

* Due dates were being calculated incorrectly sometimes when the UTC date and
  the local date differed.

* Fixed issue with `UTILS.previous_instance` and
  `UTILS.previous_test_list_instance` would not be fetched if they were
  completed within the last minute.  

Service Log
~~~~~~~~~~~

* Fixed a bug with Return To Service work forms being populated with incorrect data
* The first Service Event Status created will now automatically be set to the default
* The Service Type field was being incorrectly when entering a new service
  event using a Service Log Template without a Service Type set. This has been fixed.

Faults
~~~~~~

* Fault Type codes are now required to be unique.  A migration has been added
  to update the code to a unique value for any duplicate fault codes.
* Fault ID column size has been reduced in the fault list views
* Fault review users are now shown as full names instead of usernames where possible
* The ability to create new fault types on the fly when entering faults is
  now restricted to users with the "Can Add Fault Type" permission
* Fault type matches are now case insensitive and surrounding whitespace will be stripped
* Fix fault table ordering and search issues with Description & Review Status columns


Parts
~~~~~

Parts tables now allow you to sort/filter by room

API
~~~

* Fixed a file upload API bug where QATrack+ would try to base64 decode a null value
* The UnitTestCollection API end point should no longer return duplicated results.
* The AutoReviewRuleSetFilter API end point has been fixed.
* Fixed the `fault_types` field of the API's FaultSerializer
* The API schema view will no longer throw a 500 error.
* Submitting a null or blank comment when performing QA via the API (e.g. with
  post data like `{..., "comment": ""}`) would previously result in a 400 Bad
  Request error being returned.  This has been adjusted so that a null or blank
  comment is now valid (no comment will be created) and will not block the QA
  Session from being created.

Reports
~~~~~~~

* The Active filter for Service Log Scheduling report filters worked for "Both"
  but not "Yes" or "No". This has now been fixed.  In addition, the wrong set
  of filters was being displayed for the Next Due Dates for Scheduled Service
  Events report.  This has also been addressed.

* Reports now respect the active/inactive status of units as well as the 
  active/inactive status of test list assignments.

* Units are now displayed correctly in the test instance report filters.

* A Chrome update caused the PDF report generation to fail due to trying to access
  already opened files. This has been fixed.

* If the "Difference" column is shown when reviewing QA (i.e. `REVIEW_DIFF_COL
  = True`) then the test list instance details report will now also show the
  difference column.

* Fixed an issue with scheduled reports failing for some report types

* Fixed an issue with Excel report emails failing

* Add new 3 month, 6 month, 90 days, and 180 days date filters 


Miscellaneous
~~~~~~~~~~~~~

* A few documentation typo fixes
* Fixed a permissions check for deleting faults
* Reviewing faults now use the term "Acknowledge" instead of "Approve"
* Admin access will no longer be required to access the page for editing units available times.
* A permissions check for editing unit available times has been fixed. Anyone with the
  'Change Unit Available Time' permission should be able to edit available times now.


QATrack+ v3.1.0.1 Release Notes
-------------------------------

.. _release_notes_3101:

* Attempt to fix an issue with Django Q not being able to find report types on Windows


QATrack+ v3.1.0 Release Notes
-----------------------------

.. _release_notes_31:


Acknowledgements
~~~~~~~~~~~~~~~~

Thank you to the many people who suggested new features, contributed bug
reports, and helped out testing this release. Thank you also to all of you who
waited patiently and provided words of encouragement in the 2 years since the
last major QATrack+ release!

Details of the v3.1.0 release
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

New version numbering
.....................

Given that QATrack+ is now a mature and featureful application, we are
eliminating the `0.` from the version number and moving from v0.3.0 to v3.1.0.

Moving to GitHub
................

QATrack+ is migrating from BitBucket to
[GitHub](https://github.com/qatrackplus/qatrackplus/).  As part of your update
process you will be instructed to update your `origin` url (`git remote set-url
origin https://github.com/qatrackplus/qatrackplus.git`).


Deprecations & Discontinuations
...............................

* Python 3.4 & 3.5, 3.6: Python 3.4 & 3.5 are no longer receiving updates and
  therefore QATrack+ will no longer be supporting those Python versions. It is
  also recommended that Python 3.7-3.10 be used on Windows as it simplifies
  the install process.

* The settings `AD_DEBUG` & `AD_DEBUG_FILE` are no longer used.  Instead,
  information is now logged to an 'auth.log' file.


Major Features
^^^^^^^^^^^^^^

* A new :ref:`Reports <reports>` tool has been added for generating and
  scheduling PDF & Excel reports.  As part of this move the following
  features have now been moved to a report rather than a standalone page:

    * Paper Backup Forms

* A new :ref:`Query Tool <reports-query_tool>` has been added for advanced
  query and reporting.  (You must set :ref:`USE_SQL_REPORTS =
  True<qatrack-config>` in your local_settings.py file to use this feature).

* :ref:`Notifications <notifications>` have been expanded & improved.
    * You can now send notifications on test lists being completed.
    * You can now specify to send notifications to individual users as well as groups.
    * You can now specify that a given notifications will only be sent for
      specific units or test lists.
    * New QC Scheduling & Unreviewed QC Notices.
    * Service event creation & update notices.
    * Parts low inventory notices.
    * Machine faults

* A new :ref:`Autosave <auto_save>` feature has been implemented to
  automatically save test list instance data temporarily to prevent data loss
  when a user mistakenly navigates away from the page while entering QC data.

* A new :ref:`Users & Groups Page <auth_users_groups_app>` has been added to simplify
  the management of Group membership and group permissions.

* A new :ref:`Fault log feature <fault_log>` for recording machine faults.

* You can now create :ref:`Service Event Templates and schedule them
  <sl_template_schedules>` in a similar manner to scheduling QC work.


Non backwards compatible changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Composite Tests will now raise an error if they return anything other than a
  numerical value, None, or an empty string ("").  Previously it was possible
  to return e.g. a string which would have resulted in the test being skipped.
  If you were relying on this behaviour, you need to switch to using a
  :ref:`String Composite/JSON <qa_string_comp_json>` test type instead.

* The `day` key is now required when performing a Test List Cycle via the API

* Upload tests can not have reference/tolerance values set.  Allowing this originally
  was an implementation oversight.

* :ref:`EMAIL_NOTIFICATION_SENDER <email_notification_settings>` must be set to 
  a valid email address, not just a name.


Tests & Test Lists
^^^^^^^^^^^^^^^^^^

* New test types including:

    * :ref:`Date and Date & Time test types <qa_tests>` to allow users to
      select dates/times with a calendar widget.  These test results will be
      available in calculation contexts as Python date, and datetime values
      respectively.

    * :ref:`Wraparound test type <qa_tests>` have been added.  This test type
      allows you to define a test that "wraps around" at a minimum and maximum
      value.  This type of test is useful for example if you have a
      collimator/gantry readout test and want to consider 359.9 deg a 0.1 deg
      difference from a 0 deg reference.

* A new "Display Name" field has been added to tests.  This is an optional
  field where you can add text describing how a test should be displayed when
  performing or reviewing. Having a separate name & display name allows you to
  create tests with descriptive names that are easy to find in the admin area,
  but use a more succinct name when performing a Test List. If left blank, the
  test name will be used.

* A new "Require Comment" option has been added to force users to enter
  a comment before submitting a test.

* It is now possible to perform a test and not have the due date advanced
  by de-selecting the "Include for Scheduling" option.

* Calculation procedures are now syntax checked, and automatically formatted
  using `Black <https://black.readthedocs.io>`_.

* Numerical tests now have an optional :ref:`Formatting <qa_test_formatting>`
  field to control how their results are displayed.  For example a test with a
  formatting of "%.2E" will use scientific notation with 2 decimal places (3
  sig figures).

* Non-calculated test types (e.g. simple numerical, multiple choice, string,
  etc) may now use the `calculation_procedure` to set :ref:`default initial
  values <qa_default_values>`.

* Added :ref:`UTILS.set_skip and UTILS.get_skip <composite_tests>` functions for
  setting/getting skip status of tests.

* Using `UTILS.set_comment` in a calculation will now open the comment box on
  the front end.

* Setting the `Warning message` field to blank on a `TestList` will now prevent
  a warning message/banner from being shown when tests are at action level.

* Calculated tests are now included in Paper Backup Forms (now a Report) by default

* Frequency dropdown lists when choosing a unit to perform QC on will now only
  show *Ad Hoc* if that unit has ad hoc test lists assigned

* There are new :ref:`Tree Views <qa_tree_views>` available (under the Perform QC
  menu) for viewing/selecting QC assigned to units.  

* There is a new  `MAX_TESTS_PER_TESTLIST` setting (default is 250 tests per
  test list)

Review & Approval
^^^^^^^^^^^^^^^^^

* Test.auto_review has been replaced by new AutoReviewRuleSet's that allow you
  to apply different AutoReviewRules to different tests. For more information
  see the :ref:`Auto Review page <qa_auto_review>`.

* A new :ref:`Bulk Review <qa_perform_bulk_review>` feature has been added to
  allow setting review & approval status for multiple test list instances at
  the same time.

* New management commands `review_all_unreviewed` and `clear_in_progress` have
  been added. `review_all_unreviewed` updates the status of all unreviewed test
  list instances, while `clear_in_progress` will delete all in progress test
  lists.


Units & Unit Types
^^^^^^^^^^^^^^^^^^

* A new :ref:`Collapse <unit_type>` option has been added to the Unit Type model
  to allow collapsing less frequency used unit types in user interface.

* Unit modalities are now labeled as `Treatment or Imaging Modality`


UI Changes
^^^^^^^^^^

* QA -> QC:  In most places in the UI the initials QA have been replaced by QC.
  This change was made to reflect that while QATrack+ is a tool for managing
  the QA program of radiation therapy programs, the data collected in QATrack+
  is QC data.

* Improved the ordering and organization of unit, frequency, and test lists
  fields when assigning a test list to a unit. Also improve UnitType dropdown
  for Unit Admin.

* The Unit admin page now has "Save as New" as an option to make it easier to
  create new units using an existing unit as a template.  You can also now
  leave the unit number blank to have it assigned automatically.

* **Staff Status** has been renamed to **Admin Status** to reflect the fact
  that almost all QATrack+ users are "Staff"!

* Test Instance points with comments associated with them are now highlighed in
  charts

* Clicking on a chart link beside a tests history will now set the date range
  for the chart to the larger of a span of 1 year, or span between the first
  and last history items.  This results in a chart of say the last 5 years of
  data for an annual QA item rather than just the single point from the most
  recent year.

* Keyboard entry of dates is now permitted for Work Started & Work Completed dates
  when performing QC

* New dropdown on Unit selection buttons to allow selecting QC to perform based
  on Test categories.

* A calculation status icon has been added (spins when calculations are being
  performed).

* Add test type css class to test rows.  Allows you to target different test
  types in site.css like:

  .. code-block:: css

        .qa-boolean, .qa-numerical {
            background-color: rgba(0, 0, 0, 0.05);
        }

* The *In Progress* label will now only display the count of in progress test lists
  visible to the users rather than the total count.

* History & Unreviewed listing pages will now show a paperclip icon if the test list instance
  has at least one attachment.

* ID attributes have been added to many elements on the pages for performing/editing test lists
  to make them easier to target with JavaScript.

* For installations with Units assigned to multiple 'Sites', a new 'Site'
  column has been added to many of the views used for selecting TestList
  assignments and TestListInstances.

Admin Changes
^^^^^^^^^^^^^

* Inline links to edit and delete foreign key choices have been disabled in all
  QATrack+ admin models. Editing or deleting a foreign key object here has
  always been a poor workflow that lead to confusion for users.

* Setting multiple references & tolerances now allows removing tolerances.

* Setting multiple references & tolerances will now include an entry in that
  UnitTestInfo's change log


API Changes
^^^^^^^^^^^

* A number of bug in the API have been fixed including:

  * a bug which was causing extra information to be returned for list views has
    been fixed.  This may require you to adjust scripts if you were relying on:

    - permissions or user_set data present in the Groups list view
    - first_name, last_name, date_joined, permissions in the User List view
    - Fields other than name, number, or site in the Unit list

  * Bugs with filtering for exact matches of search strings have been resolved.

  * First Name & Last Name have been added to the user-list api view

  * When dependencies of a composite test are skipped and the composite test itself
    is not skipped, an error letting the user know to skip the composite test
    explicitly is now shown.

* The UnitTestCollection API results now include "next_day" and "next_test_list"
  parameters to make it simple to determine which test list is to be performed
  next in a test list cycle.

* The TestList API results now includes a field "test_lists" which is 
  a list of all the sublist test lists for that TestList.

* The banner at the top of the browsable API now says "QATrack+ API" rather
  than Django Rest Framework and now the link directs to the main site rather
  than DRFs site.

* It is now possible to perform a test and not have the due date advanced by
  setting `"include_for_scheduling": False,` in your API post data.

* The `day` key is now required when performing a Test List Cycle via the API


Service Log & Parts
^^^^^^^^^^^^^^^^^^^

* The `USE_SERVICE_LOG` and `USE_PARTS` settings have been removed.  Permissions
  are suitable for hiding the UI elements if you don't want to use service log
  or parts, but having these settings can complicate some views and testing.

* Added option to :ref:`Group Linkers <sl_linkers>` to make a given Group
  Linker required when submitting a ServiceEvent.

* There is a new `New or Used` field on Parts to allow you to track new and
  used inventories of the same part separately.

* A new setting :ref:`setting_sl_allow_blank_service_area` has been added to
  optionally allow users to submit ServiceEvents without a ServiceArea set
  explicitly.

* A new setting :ref:`setting_sl_allow_blank_service_type` has been added to
  optionally allow users to submit ServiceEvents without a ServiceType set
  explicitly.

* Parts Supplier details have been expanded to include phone numbers, website,
  address and contact information

* Part supplier details pages have been added to show what parts are available
  from each supplier as well as company & contact details.

* You may now add attachments & images to Parts.  Images will be shown inline
  in the parts listing table and parts detail pages.

* :ref:`Service Log Status <sl_statuses>` now have an order field to allow you 

* You can now create :ref:`Service Event Templates and schedule them
  <sl_template_schedules>` in a similar manner to scheduling QC work.

* There is now an app for :ref:`logging machine faults <fault_log>`.

Authentication
^^^^^^^^^^^^^^

* The default authentication backend setting is now:

  .. code-block:: python

    AUTHENTICATION_BACKENDS = (
        'qatrack.accounts.backends.QATrackAccountBackend',
    )

  the `QATrackAccountBackend` is a simple wrapper around the Django ModelBackend
  to allow usernames to be transformed prior to authentication.  The transform
  is controlled by the :ref:`ACCOUNTS_CLEAN_USERNAME <accounts_clean_username>` settings.

* A new :ref:`ACCOUNTS_SELF_REGISTER <accounts_self_register>` setting has been
  added to control whether users are allowed to register their own accounts.

* A new :ref:`ACCOUNTS_PASSWORD_RESET <accounts_password_reset>` setting has been
  added to control whether users are allowed to reset or change their own passwords.

* Users can now automatically be added to QATrack+ groups based
  on their AD group memberships using . :ref:`Active Directory Groups to QATrack+ Group Map <auth_ad_groups>`'s

* The :ref:`AD_MEMBERSHIP_REQ <settings_ad>` was previously not functional and 
  has now been replaced by :ref:`Qualifying Groups <auth_ad_qualifying_groups>`'s

* When a user logs in through the AD backend, their email address, first name,
  and lastname will be updated to match the values found in Active Directory.

* The `DEFAULT_GROUP_NAMES` setting has been removed.  Instead, QATrack+ groups
  now have a :ref:`default group flag <auth_groups>`.  Anytime a user logs into
  QATrack+, they will automatically be added to any group with this flag set.

Other Minor Features & Bugs Fixed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Fixed bug with control charts and null valued / skipped tests. #506
* Fixed bug with selecting Test List Cycle days from sidebar menu

* QATrack+ by default will now use the database for caching rather than the
  filesystem.  This should have comparable or better performance and eliminate
  the occassional 500 errors generated on Windows servers due to file
  permissions & access issues.

* Some python packages have been updated
    * pydicom updated to 2.1.2
    * numpy updated to 1.20.0
    * matplotlib updated to 3.3.4
    * scipy updated to 1.5.4


What didn't make it into this release?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Translations** Unfortunately there is still quite a bit of work to be done
  in order to get QATrack+ translated into other languages.  Translations are
  currently low on the developers priority list so without outside
  contributions it is hard to say when this will be completed. However,
  incremental progress is being made in this direction and templates
  and strings are gradually getting marked for translation.


QATrack+ v0.3.0.18 Release Notes
--------------------------------

- Fixed the UnitTestCollection queryset in the API
- Updated requirements to work with Python 3.7 & new versions of pip

QATrack+ v0.3.0.18 Release Notes
--------------------------------

- Fixed a bug where Test Lists from Test List Cycles with Ad-Hoc frequency
  would not show up when charting

QATrack+ v0.3.0.16 Release Notes
--------------------------------

- Allow disabling warning message by setting TestList.warning_message blank
- Add test type to html class for qa-valuerows so they can more
  easily be targeted in JavaScript code.


QATrack+ v0.3.0.15 Release Notes
--------------------------------

- The Active Unit Test Info filter was fixed
- Fixed minimum width of Category display when performing QC tests
- Added new setting `CATEGORY_FIRST_OF_GROUP_ONLY`.  When True,
  if there is a group of sequential tests with the same category, only
  the top most category name will be shown to allow better visual
  separation of groups of categories.  Currently this defaults to False
  to maintain current behaviour but this will default to True for the
  v3.1.0 release.

Upgrading to v0.3.0.15 from v0.3.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you haven't upgraded to v0.3.0 yet see instructions for v0.3.0 below.  If
you've already upgraded to v0.3.0 then to upgrade to v0.3.0.15:

#. Open shell and activate your Python 3 virtual environment then:
#.  .. code-block:: bash

        git fetch origin
        git checkout v0.3.0.15
        python manage.py collectstatic
        python manage.py clearcache

#. On Linux `sudo service apache2 restart` on Windows, restart QATrack3 CherryPy Service


QATrack+ v0.3.0.14 Release Notes
--------------------------------

- A patch was made to fix a security flaw in LDAP/Active Directory
  Authentication.  This patch is only required if you use LDAP/Active Directory
  for authenticating your users.

  To patch your system, please follow the following instructions for your version:

    - v0.3.0.x:

        - Windows. Open a Powershell Window then:

            .. code-block:: bash

                cd C:\deploy
                .\venvs\qatrack3\Script\Activate.ps1
                cd qatrackplus
                git fetch origin
                git checkout v0.3.0.14
                python manage.py shell -c "from qatrack.accounts.utils import fix_ldap_passwords; fix_ldap_passwords()"
                python manage.py collectstatic

            then restart the CherryPy service

        - Linux. Open a terminal:

            .. code-block:: bash

                cd ~/web/qatrackplus
                source ~/venvs/qatrack3/bin/activate
                git fetch origin
                git checkout v0.3.0.14
                python manage.py shell -c "from qatrack.accounts.utils import fix_ldap_passwords; fix_ldap_passwords()"
                python manage.py collectstatic
                sudo service apache2 restart

    - v0.2.9.x:

        - Windows. Open a Powershell Window then:

            .. code-block:: bash

                cd C:\deploy
                .\venvs\qatrack\Script\Activate.ps1
                cd qatrackplus
                git fetch origin
                git checkout v0.2.9.2
                python manage.py shell
                >>> from qatrack.accounts.utils import fix_ldap_passwords; fix_ldap_passwords()
                >>> exit()
                python manage.py collectstatic

            then restart the CherryPy service

        - Linux. Open a terminal:

            .. code-block:: bash

                cd ~/web/qatrackplus
                source ~/venvs/qatrack3/bin/activate
                git fetch origin
                git checkout v0.2.9.2
                python manage.py shell
                >>> from qatrack.accounts.utils import fix_ldap_passwords; fix_ldap_passwords()
                >>> exit()
                python manage.py collectstatic
                sudo service apache2 restart


    - v0.2.8.x:

        - Windows. Open a Powershell Window then:

            .. code-block:: bash

                cd C:\deploy
                .\venvs\qatrack\Script\Activate.ps1
                cd qatrackplus
                git fetch origin
                git checkout v0.2.8.1
                python manage.py shell
                >>> from qatrack.accounts.utils import fix_ldap_passwords; fix_ldap_passwords()
                >>> exit()
                python manage.py collectstatic

            then restart the CherryPy service

        - Linux. Open a terminal:

            .. code-block:: bash

                cd ~/web/qatrackplus
                source ~/venvs/qatrack3/bin/activate
                git fetch origin
                git checkout v0.2.8.1
                python manage.py shell
                >>> from qatrack.accounts.utils import fix_ldap_passwords; fix_ldap_passwords()
                >>> exit()
                python manage.py collectstatic
                sudo service apache2 restart


QATrack+ v0.3.0.13 Release Notes
--------------------------------

For full details of v0.3.0 see the v0.3.0 release notes below.  v0.3.013 is
a patch to v0.3.0 that fixes a few minor issues.

- Service Events have been added to the admin so they can now be hard deleted.

- A few bugs with testpacks has been fixed including where Sublist tests were
  not created correctly when creating test packs.

- A number of bugs with the API have been fixed.

- A bug with the initial v0.3.0 migration has been fixed for those who
  have `SITE_ID ~= 1` in their settings file.

- skipped tests are now excluded by default from `UTILS.previous_test_instance`.

- Bug where the Test List Members drop down would not be populated correctly
  due to conflicting jQuery versions has been resolved.


Upgrading to v0.3.0.13 from v0.3.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you haven't upgraded to v0.3.0 yet see instructions for v0.3.0 below.  If
you've already upgraded to v0.3.0 then to upgrade to v0.3.0.13:

#. Open shell and activate your Python 3 virtual environment then:
#.  .. code-block:: bash

        git fetch origin
        git checkout v0.3.0.13
        python manage.py collectstatic
        python manage.py clearcache

#. On Linux `sudo service apache2 restart` on Windows, restart QATrack3 CherryPy Service


QATrack+ v0.3.0 Release Notes
-----------------------------

.. _release_notes_030:


It's been two years since the release of QATrack+ v0.2.9 and this release marks
the largest update to QATrack+ since the initial release in 2012. Details of
QATrack+ v0.3.0 are included below.

Acknowledgements
~~~~~~~~~~~~~~~~

Many thanks to Ryan Bottema & Crystal Angers at The Ottawa Hospital for all
their work on the development and implementation of the new Service Log app
(with guidance and QA from the rest of the Ottawa QATrack+ team!).

Thank you to `Simon Biggs <https://www.simonbiggs.net/#/>`__ for all his work
on the new experimental Docker deployment method as well as ideas and
discussions on many other features.

Thanks to all of you who provided databases for testing the data model
migration from 0.2.9 to 0.3.0. This helped catch a few DBMS specific migration
issues.  There were also a number of people who tested the migration / update
procedure before this releae which is hugely appreciated!

A big thanks also goes out to the Canadian Nuclear Safety Commission! QATrack+
was one of the recipients of the `2017 CSNC's Innovation Grant
<https://www.comp-ocpm.ca/english/news/cnsc-innovation-fund-update.htm>`__
which provided financial support for this release.

Last but certainly not least, thank you to those of you who have submitted bug
reports, made feature requests, and contributed to the many discussions on the
mailing list.


Details of the v0.3.0 release
.............................

* A new :ref:`Service Log <service_log_user>` application for tracking machine
  service events, machine down time, return to service, and more!

* A new :ref:`Parts <parts_user>` application for tracking spare parts, where
  they're located, how many are in inventory, and their vendors.

* :ref:`Sublists <qa_sublists>` have been updated and improved and can now
  have their order rearranged within the parent test list as well as optional
  visual emphasis when performing a test list.

* The user interface has been updated to be a bit more modern while hopefully
  remaining familiar to existing QATrack+ users.

* `Pylinac <http://pylinac.readthedocs.io/en/latest/index.html>`_ is now
  installed by default.  Images can be uploaded, analyzed, and displayed inline
  within test lists.

* Experimental support for importing/exporting :ref:`Testpacks
  <testpack_admin>` for exchanging test configurations with other QATrack+
  installations.

* An :ref:`Application Programming Interface (API) <qatrack_api>` has been
  added for allowing external applications and scripts to access and upload
  data to your QATrack+ server.

* When reviewing data by Due Status you can :issues:`now filter by unit <211>`.

* After creating a Unit Test Collection, it is :issues:`no longer possible to
  change the test list (cycle) assigned to it <245>`.  This is in order to
  prevent unintended data loss.

* You can now assign a :issues:`tolerance to boolean tests <214>`.

* The ability to save test lists is now an :ref:`assignable user permission
  <permissions_admin>`.

* Entire units can now be marked as :issues:`inactive <84>` to make it easy to
  hide units when they are decomissioned.

* Hidden tests :issues:`can now be autoreviewed <286>`.

* When choosing a unit to peform QA on, rather than showing all defined
  frequencies, the drop down lists for test frequencies are now limited
  :issues:`to frequencies of test lists assigned to that unit <274>`.

* A new "experimental" method of deploying QATrack+ using Docker is available.
  This method makes it very easy to get a complete QATrack+ installation up and
  running.  Currently marked as experimental as it has not been deployed in
  production anywhere.  Thank you very much to Simon Biggs for putting this
  idea forward and then getting it all implemented in a sensible way!

* When a reference or tolerance for a test is updated, the history of the users
  who made the change, when the changes was made, the previous reference and
  tolerance, and  an optional comment :issues:`are now stored <49>`.

* It's now possible to set (or read) the comment for a test instance from the
  :issues:`tests calculation procedure <280>`.

* Default email notifications are now sent as html emails with a link to the
  :issues:`relevant test list instance <283>`

* Notification emails are :issues:`no longer sent to inactives users <246>`.

* When performing a test list, the number of existing in-progress sessions for
  the same test list :issues:`is now shown in the UI <208>`. The total number
  of test lists in progress is also now shown in the main drop down menus.

* Comments can now be added when reviewing test list instances and comments on
  test list instances now :issues:`<record the username and timestamp <181>` of
  the comment.

* If a composite test or upload test generates a "Server Error", the error can
  now be seen by :issues:`hovering your mouse over the Status column for the
  test <272>`.

* The UX for deleting a test list :issues:`has been improved <308>`.

* Upload tests now have two context variables available `FILE` and `BIN_FILE`,
  the latter being a file instances opened in binary rather than text mode.
  Any existing upload tests that you have which assume a binary file type will
  need to be updated to use `BIN_FILE`. More details are available in the
  v0.3.0 installation docs.

* Mainstream support for Python 2 is ending in 2020 and as such QATrack+ has
  been updated to use Python 3.4-3.6.

* The complete list of bugs/features can be found on `BitBucket
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues?page=4&milestone=0.3.0>`_


Upgrading to v0.3.0
~~~~~~~~~~~~~~~~~~~

For instructions on upgrading to QATrack+ 0.3.0 please see the installation
docs for your platform.


QATrack+ v0.2.9 Release Notes
-----------------------------

.. _release_notes_029:

There have been many bug fixes and improvements to QATrack+ made since the
version 0.2.8. For the complete details you can check out the issue tracker
for issues tagged 0.2.9.

Special thanks for this release to Zacharias Chalampalakis for contributing a patch
to make the warning message shown when a test is at action level configurable.

Also, big thanks to Ryan Bottema in Ottawa who has taken over my previous role
at the Ottawa Hospital and has made many contributions to this release and been
crucial in finally getting it out the door.

As always Crystal Angers has been a big help in testing and critical analysis
of new features.


Details of 0.2.9 below:

* Multiple choices tests now store their results `as the test value rather than
  the index
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/162/adding-new-multiple-choice-options-can>`_
  of the choice.  It is important that you update any composite tests that rely
  on multiple choice test results after this upgrade (see Upgrade Instructions
  below)

* Unit modalities `are now free text fields
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/110/change-unit-modality-to-free-text-field>`_
  instead of forcing you to select particle/energy.

* If you attempt to access a QATrack+ page but are logged out, `you will be
  redirected to that page after logging in
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/154/redirect-after-login>`_

* You can now add `REVIEW_DIFF_COL = True` to your local_settings.py file to
  `enable an extra column showing the difference from reference
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/155/add-deviation-from-reference-to-testlist>`_
  when reviewing tests list

* Users sessions will be `renewed anytime they are active
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/165/refresh-session-after-any-activity-rather>`_
  on the QATrack+ site rather than just when they perform QA (prevents being
  logged out automatically)

* Changing a Test's type is now limited to `only allow changes to similar test
  types
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/168/changes-between-test-types-needs-to-be>`_
  (e.g. numerical -> composite is allowed but numerical -> string is not)

* By default `inactive test lists are no longer shown
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/170/add-filter-to-not-display-by-default>`_
  in the default review list

* Bulk deletion of UnitTestInfo objects in the admin `has been disabled
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/171/disable-bulk-delete-of-unittestinfo>`_
  to prevent possible data loss

* Only active UnitTestInfo objects will be `shown in the admin
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/172/make-unittestinfo-list-in-admin-only-show>`_
  by default

* You can now `view test list comments
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/175/view-comments>`_
  in a pop over by hovering your mouse over the comment icon

* You can now filter Test objects in the admin by whether or not `they belong
  to any active TestList's
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/177/test-search>`_ or
  not

* If a comment is included when performing a test list than `manual review will
  be required
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/179/auto-review-exception-for-tests-with>`_
  regardless of auto-review settings

* Inactive tests can now be `filtered on the charts page
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/183/filter-out-inactive-tests-in-the-chart>`_

* There are many new filters available in the admin section

* Permissions for reviewing and viewing the program overview `have been split
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/194/separate-permisssions-for-review-and>`_

* Individual tests can now be configured to `always allow skipping without a
  comment
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/195/skipping-without-comment-for-some-but-not>`_
  (regardless of the users permissions)

* You can now `set a custom label
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/198/allow-customization-of-testlist-cycle-drop>`_
  for the "Choose Day" drop down label when performing a test list from a
  cycle.

* You can now sort test lists by due date

* You can now `customize the test status display
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/200/tolerance-action-level-naming>`_
  (default remains Act/Tol/OK)

* Test value input fields should now be more `mobile device friendly
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/210/change-text-input-type-to-number-for>`_

* pydicom is now available in the `default calculation context
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/219/add-pydicom-to-default-calculation-context>`_
  (along with numpy & scipy)

* You can now filter test lists to review `by which groups the test lists are
  visible to
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues/227/visible-to>`_

A more complete list of bugs fixed and features added can be found `in the
issues tracker
<https://bitbucket.org/tohccmedphys/qatrackplus/issues?milestone=0.2.9>`_!

Deprecation Notices
~~~~~~~~~~~~~~~~~~~

As QATrack+, Python & Django and the web continue to evolve, occassionally we need to deprecate some of the versions of Python & web browsers we support.
The next major release of QATrack+ will no longer officially support the following items:

- Python 2.6 (Python 2.7 & 3.4+ only): In order to provide support for Python 3 we will be dropping support for Python 2.6
- IE7-IE10 (IE 11+ Only): IE7-IE10 are no longer supported by Microsoft and we will no longer be testing these platforms.

Upgrade Instructions
~~~~~~~~~~~~~~~~~~~~

For instructions on how to upgrade from v0.2.8 `please see the wiki <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.9/release-notes.md>`_


QATrack+ v0.2.8 Release Notes
-----------------------------

.. _release_notes_028:


.. _note:

    This release introduces some database schema changes. The database
    migrations have been tested on SQLServer, PostgreSQL, MySQL & SQLite but it
    is important that you:

    BACK UP YOUR DATABASE BEFORE ATTEMPTING THIS UPGRADE

There are lots of minor enhancements & a number of new features in this release
of QATrack+.

Special thanks for this release go to Wenze van Klink from VU Medisch Centrum
Amsterdam.  Wenze contributed a couple of great features to QATrack+ for this
release including:

* The ability to easily copy references & tolerance from one Unit to another.
  A nice time saver!

* The ability to set references and tolerances for multiple tests at the same
  time.  Want to set 20 tests to have a reference value of 100? Now you can do
  it with just a few clicks.

* Display uploaded images (jpg, png, gif) on the test list page.

* a number of other bug fixes & minor features.

Great work Wenze...your contributions are greatly appreciated!

Also of note, Gaspar Sánchez Merino has produced a Spanish translation of the
QATrack+ documentation.  Thanks a lot Gaspar!  You can find the translation on
`Gaspar's BitBucket page
<https://bitbucket.org/gasparsanchez/qatrackplus/wiki/users/guide.md>`_.

Here's a list of some of the changes in this release:

* The documentation has been split into different versions (corresponding to
  QATrack+ releases) to accomodate users who are not running the latest version
  of QATrack+.

* You can now `embed uploaded images right on the test list page
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/tests>`_

* You can now `choose to hide tests from the list of tests to plot
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/tests>`_.
  Handy to limit the chart test selection lists to only those tests you are
  interested in plotting.

* There is now an `"Auto Review" feature
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/auto_review>`_
  that can be configured so that only test which are at tolerance or action
  levels will be placed in the review queue.

* Page load speeds for the charting page have been greatly improved for large
  databases

* You can now `configure your site to use icons
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/deployment/settings>`__
  in addition to colors to indicate pass/fail & due/overdue. This should help
  with usability for color blind users.  Thanks to Eric Reynard for the great
  suggestion! Examples of the icons can be seen on `BitBucket
  <https://bitbucket.org/tohccmedphys/qatrackplus/pull-request/11/add-icons-to-reduce-dependence-on-red/diff>`__

* Python code snippets and html test/test list descriptions are `now syntax
  highlighted on modern browsers
  <https://bitbucket.org/tohccmedphys/qatrackplus/issue/78/integrate-ace-or-code-mirror-for>`_

* Composite & constant tests no `longer need to be skipped manually
  <https://bitbucket.org/tohccmedphys/qatrackplus/issue/98/skip-box-for-composite-test>`_

* When charting you can now `combine data for the same test from different test
  lists
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/users/charts>`_
  (thanks to Eric Reynard for the suggestion)

* Data can now be `plotted relative to its reference value
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/users/charts>`_
  (thanks to Balazs Nyiri for the suggestion)

* CSV export files should now work on IE8 & 9

* A new permission has been added to control `who can review their own test
  results
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/auth>`_

* It's now possible to easily `copy references and tolerances between units
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/setting_refs_and_tols>`_

* Easily set references & tolerances for `multiple tests at the same time
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/setting_refs_and_tols>`_

* You can now tweak the look of your QATrack+ site with css using a `site
  specific css file
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/deployment/site_css.md>`_

* You can now configure your site to `order the Units on the "Choose Unit" page
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/deployment/settings>`_
  by number or name.

* QATrack+ now is using a file based cache to decrease page load times. By
  default the cache data is located at qatrack/cache/cache\_data/ but this `can
  be changed if required
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/deployment/settings>`_.

* You can now assign multiple choice tolerances to string/string composite test
  types (thanks to Elizabeth McKenzie for the suggestion).

* You can now access reference and tolerance values for `tests in your
  calculated tests
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/calculated.md>`_
  (thanks to Andrew Alexander from Saskatoon for the suggestion)

* a number of other bug fixes and performance enhancements


Upgrading to v0.2.8
~~~~~~~~~~~~~~~~~~~

*Note: If any of these steps results in an error, \*stop\* and figure out why before
carrying on to the next step!*

From the git bash command shell (with your QATrack+ virtual env activated!):

1) git pull origin master
2) pip install -r requirements/base.txt
3) python manage.py syncdb
4) python manage.py migrate
5) python manage.py collectstatic
6) restart the QATrack+ app (i.e. the CherryPy service or Apache or gunicorn or...)


QATrack+ v0.2.7 Release Notes
-----------------------------

.. _release_notes_027:

**Note: this release introduces some database schema changes.  It is a good idea to BACK UP
YOUR DATABASE BEFORE ATTEMPTING THIS UPGRADE**

Version 0.2.7 has a quite a few improvements to the code base behind the
scenes, some new features and a number of bug fixes. Please see the guide to
upgrading to version 0.2.7 below.

A note on QATrack+ and security is now `available on the wiki
<https://bitbucket.org/tohccmedphys/qatrackplus/wiki/deployment/security.md>`_.

Special thanks for this release go to Eric Reynard of Prince Edward Island.
Eric has contributed a `new authentication backend and tutorial
<https://bitbucket.org/tohccmedphys/qatrackplus/wiki/deployment/windows/iisFastCGI>`_
on running QATrack+ with IIS, FastCGI and Windows Integrated Authentication.
Thanks Eric!

New Features & Bugs Fixed
~~~~~~~~~~~~~~~~~~~~~~~~~

* Three new `test types
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/test.md>`_ have
  been added:

    * File upload: Allows you to upload and process arbitrary files as part of a test list
    * String: Allows you to save short text snippets as test results
    * String Composite: A composite test for text rather than numerical values

* `Composite tests
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/test.md>`_ no
  longer need to assign to a `result` variable. Instead you can just assign the
  result to the composite test macro name (e.g. `my_test = 42` is now a valid
  calculation procedure). This is now the recommended way to write calculation
  macros.
* Tests with calculated values now have `a 'META' variable
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/calculated.md>`_
  available in the calculation context that includes some useful information
  about the test list being performed.
* Easy export of historical test results to CSV files
* New tool for creating basic paper backup QA forms to be used in the event of
  a server outage. See the `paper backup wiki page <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/users/paper_backup_forms.md>`_
  for more information.  This feature is currently quite primitive and
  suggestions on how to improve it are welcome!
* TestListCycle's can now contain the same TestList multiple times. Thanks to Darcy Mason for reporting this bug.
* Unit's that have no active TestList's will no longer appear on the Unit selection page
* Changes to Reference & Tolerances:
    * Tolerances no longer require all 4 of the tolerance/action levels (Act
      Low, Tol Low, Act High, Tol High) to be set making it possible to create
      pass/fail only, pass/tolerance only and one-sided tolerances. See the
      `Tolerances wiki page
      <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/tolerances.md>`_
      for more information.
    * Duplicate tolerances can no longer be created (there is no use for
      duplicate tolerances)
    * Tolerances can no longer be named by the user and are now automatically
      given a descriptive name based on their tolerance and action levels. This
      is to help emphasize the fact that Tolerance values are not test
      specific.
    * As part of the 0.2.7 database update, all duplicate tolerance & reference
      objects in the database are going to be deleted and any test value
      currently pointing at these tolerance & reference values will be updated
      to point at the correct non-duplicated tolerance/reference.  At TOHCC
      this resulted in reducing the size of references database table by about
      90% (from ~2700 rows to ~200 rows).
* A new authentication backend using Windows Integrated Authentication has been
  added.  Thanks to Eric Reynard for contributing this!
* New user account pages for viewing permissions and updating/resetting passwords.
* Page permissions have been improved slightly and two new permisions have been added:

    * **qa | test instance | Can chart test history** (Allows users to access charts page)

    * **qa | test list instance | Can view previously completed instances**
      (Allows users to view but not edit or review (change the status) of
      historical results.  Please see the `wiki
      <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/auth.md>`__
      for more information.

* Page load time reduced by using more efficient unreviewed count query
* Charts page now allows plotting of data for tests which are no longer active
* Test data is now grouped by TestList when generating charts (i.e. multiple lines are
    produced if the same Test exists in multiple TestList's)
* `Many other little bugs fixed :) <https://bitbucket.org/tohccmedphys/qatrackplus/issues/2?milestone=0.2.7>`_


Upgrading to v0.2.7
~~~~~~~~~~~~~~~~~~~

_Note: If any of these steps results in an error, stop and figure out why before
carrying on to the next step!_

From the git bash command shell (with your QATrack+ virtual env activated!):

#. git pull origin master
#. pip install -r requirements/base.txt
#. python manage.py syncdb
#. python manage.py migrate
#. python manage.py collectstatic
#. restart the QATrack+ app (i.e. the CherryPy service or Apache or gunicorn ...)
#. In the `Admin --> Auth --> Groups` section of the website grant the new permissions

    * **qa | test instance | Can chart test history**
    * **qa | test list instance | Can view previously completed instances**

    to any groups that require this functionality.  See the `Managing Users &
    Groups page
    <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/auth.md>`_ for
    more information on permissions.  1. In order to use the new file upload
    test type, you must configure your server to serve all requests for
    http(s)://YOURSERVER/media/\* to files in `qatrack/uploads/` directory.
    More information about this is available on the `deployment wiki pages
    <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/deployment/about.md>`_.
    If you need help with this part please post in the `QATrack+ Google group
    <https://groups.google.com/forum/?fromgroups#!forum/qatrack>`_. If you
    don't plan on using the file upload test type, this step is not required.


QATrack+ v0.2.6 Release Notes
-----------------------------

.. _release_notes_026:

**Note: this release introduces some database schema changes.  BACK UP
YOUR DATABASE BEFORE ATTEMPTING THIS UPGRADE**

v0.2.6 includes a number of bug fixes

Thank you to Eric Reynard and Darcy Mason for their bug reports.

New Features
~~~~~~~~~~~~

* You can now manually override the due date for a Test List on a Unit
* You can `turn off the auto scheduling <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/assign_to_unit.md>`_ of due dates for Test Lists on
  Units
* Test Lists no longer need to have a Frequency associated with them when
  `assigned to a Unit
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/assign_to_unit.md>`_
  (allows for ad-hoc Tests)
* new management command `auto_schedule` (see
  `wiki <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/auto-schedule.md>`_)
* Selecting a different day in a Test List Cycle  no longer requires you to click *Go*
* When references aren't visible, Users will only be shown 'OK' or 'FAIL'
  instead of 'OK', 'TOL' or 'ACT'
* Minor improvements to the charts page layout
* Reference values are now included in data displayed on chart page
* Test List description can now be displayed on the page when
  performing or reviewing QA
* Improved performance when saving data from test lists with lots of tests.
* New `permission
  <https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/auth.md>`_ **Can
  skip without comment** added to allow some
  users/groups to skip tests without adding a comment
* Comment counts are now displayed in Test List history listings
* Now only Units which have Test Lists visible to the user will be
  displayed.
* The first page of all listings is now pre-rendered for faster page
  load times
* Input lag when performing QA using IE has now been
  reduced (although it is still highly recommended that you use Chrome
  or Firefox!)
* Deploying QATrack+ under a sub directory of your server should now
  be handled a little better (requires setting FORCE\_SCRIPT\_NAME in
  your local_settings.py file)
* There is now a **View on Site** button that will allow you to go
  directly to the Perform QA page from a UnitTestCollection (Assign
  Test List to Unit) page in the admin
* Some other minor cosmetic enhancements
* majority of code now conforms with pep8

Bug Fixes
~~~~~~~~~

* Unique Char fields limited to a length of 255 to fix issue with
  MySQL
* Fixed formatting of due date displays
* Increased the precision with which data is displayed in chart tool tips
* Fixed "Absolute value" wording mixup when defining tolerances
* Fixed errors when adding new tests to a sublist
* Plotting data with one of the chart buttons will now only select the relevant
  Test Lists
* Chart reference lines are now plotted in the same colour as the actual plot line
* Fixed issue when navigating between inputs on filtered lists
* Fixed issue with missing history values for Test List cycles
* Added missing filter for "Assigned To" column on Test List listings
* The value 0 should no longer be shown in scientific notation
* Fixed issue with non linearly spaced graph data
* `various other issues
  <https://bitbucket.org/tohccmedphys/qatrackplus/issues?version=0.2.5&status=resolved&version=0.2.6>`_


To upgrade from v0.2.5
~~~~~~~~~~~~~~~~~~~~~~

**Note: this release introduces some database shema changes.  BACK UP YOUR
DATABASE BEFORE ATTEMPTING THIS UPGRADE**

From the git bash shell in the root directory of your QATrack+ project

1. git pull origin master
1. python manage syncdb
1. python manage.py migrate
1. python manage.py collectstatic


QATrack+ v0.2.5 Release Notes
-----------------------------

.. _release_notes_025:

This release fixes some issues with control charts and makes test list pages
orderable and filterable.

There are no database schema changes in this release so updating should just
be a matter of pulling the latest release from git.

Changes in this release include:

* A number of improvments to the control chart functionality have been made
* Test lists and completed sessions are now sortable & filterable without a
  page refresh.
* On the overview page, you cannow collapse/expand the Units so that you can
  review one Unit at a time.
* Scientific notation is now used to display composite test results for large &
  small values.
* The behaviour when determining whether a value exactly on a pass/tolerance or
  tolerance/fail border has been improved (see
  :issues:`issue 207 <207>`.

* numpy & scipy are now available in the composite calculation context

* All test variable names (whether they have values entered for them or not)
  are now included in the composite calculation context.
* Crash in admin when "saving as new" with missing tests has been fixed.
* default work completed date is now an hour later than default work started.
* Fixed display of work completed date for last session details (time zone issue)
* Some other bug fixes and cleanup


QATrack+ v0.2.4 Release Notes
-----------------------------

.. _release_notes_024:

This release introduces `South <http://south.aeracode.org/>`_ for managing
database schema migrations.  In order to update an existing database, you need
to do the following:

1. pip install south
2. *checkout version 0.2.4 code (e.g. git pull origin master)*
3. python manage.py syncdb
4. python manage.py migrate qa 0001 --fake
5. python manage.py migrate units 0001 --fake
6. python manage.py migrate qa

New Features
~~~~~~~~~~~~

* added South migrations
* added description field to TestInstance Status models (displayed in tooltips
  when reviewing qa)
* Added new review page for displaying Test Lists by due date
* Added new review page for displaying overall QA Program status


Bug Fixes and Clean Up
~~~~~~~~~~~~~~~~~~~~~~

* removed `salmonella <https://github.com/lincolnloop/django-salmonella>`_ urls
  from urls.py


QATrack+ v0.2.3 Release Notes
-----------------------------

.. _release_notes_023:

This release has a number of small features and bug fixes included.

New Features
~~~~~~~~~~~~

* Greatly improved permissions system.  Group/user specific permissions are no
  longer only controlled by the is_staff flag
* TestListCycle's now display the last day done
* You can now delete TestListInstances from the admin interface or when
  reviewing (redirects to admin)
* Cleaned up interface for choosing a unit a bit.


Bug Fixes
~~~~~~~~~

* Fixed js null bug when charting (see `issue #189
  <https://bitbucket.org/randlet/qatrack/issue/189/js-exception-on-generate-chart>`_)
* Fixed expiring cookie issue that could potentially `cause QA data to be lost
  when submitted
  <https://bitbucket.org/randlet/qatrack/issue/178/possible-data-loss-if-user-is-logged-out>`_.
* Deleting a UnitTestCollection no longer causes a server fault.
* `more <https://bitbucket.org/randlet/qatrack/issues?milestone=0.2.3>`_

