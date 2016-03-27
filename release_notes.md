# QATrack+ Release Notes #

## v0.3.0 ##

- note about filtering and multiple choice tests (value -> string_value)

## v0.2.8 ##

    Note: this release introduces some database schema changes. The database migrations have
    been tested on SQLServer, PostgreSQL, MySQL & SQLite but it is important that you:

    BACK UP YOUR DATABASE BEFORE ATTEMPTING THIS UPGRADE

There are lots of minor enhancements & a number of new features in this release of QATrack+.

Special thanks for this release go to Wenze van Klink from VU Medisch Centrum Amsterdam.
Wenze contributed a couple of great features to QATrack+ for this release including:

* The ability to easily copy references & tolerance from one Unit to another.  A nice time saver!
* The ability to set references and tolerances for multiple tests at the same time.
    Want to set 20 tests to have a reference value of 100? Now you can do it with just a few clicks.
* Display uploaded images (jpg, png, gif) on the test list page.
* a number of other bug fixes & minor features.

Great work Wenze...your contributions are greatly appreciated!

Also of note, Gaspar Sánchez Merino has produced a Spanish translation of the
QATrack+ documentation.  Thanks a lot Gaspar!  You can find the translation on
[Gaspar's BitBucket page](https://bitbucket.org/gasparsanchez/qatrackplus/wiki/users/guide.md).

Here's a list of some of the changes in this release:

* The documentation has been split into different versions (corresponding to QATrack+ releases) to accomodate users who are not running
the latest version of QATrack+.
* You can now [embed uploaded images right on the test list page](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/tests)
* You can now [choose to hide tests from the list of tests to plot](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/tests). Handy to limit the chart test selection lists to only those tests you are interested in plotting.
* There is now an ["Auto Review" feature](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/auto_review) that can be configured so that only test which are at tolerance or action levels will be placed in the review queue.
* Page load speeds for the charting page have been greatly improved for large databases
* You can now [configure your site to use icons](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/deployment/settings) in addition to colors to indicate pass/fail & due/overdue. This should help
with usability for color blind users.  Thanks to Eric Reynard for the great suggestion! Examples of the icons can be seen on [BitBucket](https://bitbucket.org/tohccmedphys/qatrackplus/pull-request/11/add-icons-to-reduce-dependence-on-red/diff)
* Python code snippets and html test/test list descriptions are [now syntax highlighted on modern browsers](https://bitbucket.org/tohccmedphys/qatrackplus/issue/78/integrate-ace-or-code-mirror-for)
* Composite & constant tests no [longer need to be skipped manually](https://bitbucket.org/tohccmedphys/qatrackplus/issue/98/skip-box-for-composite-test)
* When charting you can now [combine data for the same test from different test lists](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/users/charts) (thanks to Eric Reynard for the suggestion)
* Data can now be [plotted relative to its reference value](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/users/charts) (thanks to Balazs Nyiri for the suggestion)
* CSV export files should now work on IE8 & 9
* A new permission has been added to control [who can review their own test results](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/auth)
* It's now possible to easily [copy references and tolerances between units](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/setting_refs_and_tols)
* Easily set references & tolerances for [multiple tests at the same time](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/admin/setting_refs_and_tols)
* You can now tweak the look of your QATrack+ site with css using a [site specific css file](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/deployment/site_css.md)
* You can now configure your site to [order the Units on the "Choose Unit" page](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/deployment/settings) by number or name.
* QATrack+ now is using a file based cache to decrease page load times. By default
the cache data is located at qatrack/cache/cache\_data/ but this [can be changed if required](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.8/deployment/settings).
* You can now assign multiple choice tolerances to string/string composite test types (thanks to Elizabeth McKenzie for the suggestion).
* You can now access reference and tolerance values for [tests in your calculated tests](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/calculated.md) (thanks to Andrew Alexander from Saskatoon for the suggestion)
* a number of other bug fixes and performance enhancements


### Upgrading to v0.2.8 ###

_Note: If any of these steps results in an error, *stop* and figure out why before
carrying on to the next step!_

From the git bash command shell (with your QATrack+ virtual env activated!):

1. git pull origin master
1. pip install -r requirements/base.txt
1. python manage.py syncdb
1. python manage.py migrate
1. python manage.py collectstatic
1. restart the QATrack+ app (i.e. the CherryPy service or Apache or gunicorn or...)


## v0.2.7 ##

**Note: this release introduces some database schema changes.  It is a good idea to BACK UP
YOUR DATABASE BEFORE ATTEMPTING THIS UPGRADE**

Version 0.2.7 has a quite a few improvements to the code base behind the
scenes, some new features and a number of bug fixes. Please see the guide to
upgrading to version 0.2.7 below.

A note on QATrack+ and security is now
[available on the wiki](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/deployment/security.md).

Special thanks for this release go to Eric Reynard of Prince Edward Island.  Eric
has contributed a
[new authentication backend and tutorial](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/deployment/windows/iisFastCGI)
on running QATrack+ with IIS, FastCGI and Windows Integrated Authentication.  Thanks Eric!

### New Features & Bugs Fixed ###

* Three new [test types](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/test.md) have been added:
    * File upload: Allows you to upload and process arbitrary files as part of a test list
    * String: Allows you to save short text snippets as test results
    * String Composite: A composite test for text rather than numerical values
* [Composite tests](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/test.md) no longer need to assign to a `result` variable. Instead you can just assign
the result to the composite test macro name (e.g. `my_test = 42` is now a valid calculation procedure). This is now the recommended way to write calculation macros.
* Tests with calculated values now have [a `META` variable ](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/calculated.md)
available in the calculation context that includes some useful information about the test list being performed.
* Easy export of historical test results to CSV files
* New tool for creating basic paper backup QA forms to be used
    in the event of a server outage. See the
    [paper backup wiki page](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/users/paper_backup_forms.md)
    for more information.  This feature is currently quite primitive and
    suggestions on how to improve it are welcome!
* TestListCycle's can now contain the same TestList multiple times. Thanks to Darcy Mason for reporting this bug.
* Unit's that have no active TestList's will no longer appear on the Unit selection page
* Changes to Reference & Tolerances:
    * Tolerances no longer require all 4 of the tolerance/action levels
    (Act Low, Tol Low, Act High, Tol High) to be set making it possible
    to create pass/fail only, pass/tolerance only and one-sided tolerances. See the
    [Tolerances wiki page](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/tolerances.md)
    for more information.
    * Duplicate tolerances can no longer be created (there is no use for duplicate tolerances)
    * Tolerances can no longer be named by the user and are now automatically given a descriptive
    name based on their tolerance and action levels. This is to help emphasize the fact that Tolerance
    values are not test specific.
    * As part of the 0.2.7 database update, all duplicate tolerance & reference objects in the database
    are going to be deleted and any test value currently pointing at these tolerance & reference
    values will be updated to point at the correct non-duplicated tolerance/reference.  At TOHCC this
    resulted in reducing the size of references database table by about 90% (from ~2700 rows to ~200 rows).
* A new authentication backend using Windows Integrated Authentication has been added.  Thanks to Eric Reynard
    for contributing this!
* New user account pages for viewing permissions and updating/resetting passwords.
* Page permissions have been improved slightly and two new permisions have been added:
    * **qa | test instance | Can chart test history** (Allows users to access charts page)
    * **qa | test list instance | Can view previously completed instances** (Allows users to view but not edit or review (change the status) of historical results.
Please see the [wiki](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/auth.md) for more information.
* Page load time reduced by using more efficient unreviewed count query
* Charts page now allows plotting of data for tests which are no longer active
* Test data is now grouped by TestList when generating charts (i.e. multiple lines are
    produced if the same Test exists in multiple TestList's)
* [Many other little bugs fixed :)](https://bitbucket.org/tohccmedphys/qatrackplus/issues/2?milestone=0.2.7)


### Upgrading to v0.2.7 ###

_Note: If any of these steps results in an error, stop and figure out why before
carrying on to the next step!_

From the git bash command shell (with your QATrack+ virtual env activated!):

1. git pull origin master
1. pip install -r requirements/base.txt
1. python manage.py syncdb
1. python manage.py migrate
1. python manage.py collectstatic
1. restart the QATrack+ app (i.e. the CherryPy service or Apache or gunicorn ...)
1. In the `Admin --> Auth --> Groups` section of the website grant the new permissions
    * **qa | test instance | Can chart test history**
    * **qa | test list instance | Can view previously completed instances**

    to any groups that require this functionality.  See the
    [Managing Users & Groups page](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/auth.md)
    for more information on permissions.
1. In order to use the new file upload test type, you must configure your server to serve all requests for http(s)://YOURSERVER/media/\* to files in `qatrack/uploads/` directory.
More information about this is available on the
[deployment wiki pages](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/deployment/about.md).
If you need help with this part please post in the
[QATrack+ Google group](https://groups.google.com/forum/?fromgroups#!forum/qatrack). If you don't
    plan on using the file upload test type, this step is not required.

## v0.2.6 ##

**Note: this release introduces some database schema changes.  BACK UP
YOUR DATABASE BEFORE ATTEMPTING THIS UPGRADE**

v0.2.6 includes a number of bug fixes

Thank you to Eric Reynard and Darcy Mason for their bug reports.

### New Features ###

* You can now manually override the due date for a Test List on a Unit
* You can [turn off the auto scheduling](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/assign_to_unit.md) of due dates for Test Lists on
  Units
* Test Lists no longer need to have a Frequency associated with them
  when [assigned to a Unit](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/assign_to_unit.md) (allows for ad-hoc Tests)
* new management command `auto_schedule` (see [wiki](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/auto-schedule.md))
* Selecting a different day in a Test List Cycle  no longer requires you to click *Go*
* When references aren't visible, Users will only be shown 'OK' or 'FAIL' instead of 'OK', 'TOL' or 'ACT'
* Minor improvements to the charts page layout
* Reference values are now included in data displayed on chart page
* Test List description can now be displayed on the page when
  performing or reviewing QA
* Improved performance when saving data from test lists with lots of tests.
* New [permission](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/admin/auth.md) **Can skip without comment** added to allow some
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

### Bug Fixes ###

* Unique Char fields limited to a length of 255 to fix issue with
  MySQL
* Fixed formatting of due date displays
* Increased the precision with which data is displayed in chart tool tips
* Fixed "Absolute value" wording mixup when defining tolerances
* Fixed errors when adding new tests to a sublist
* Plotting data with one of the chart buttons will now only select the relevant Test Lists
* Chart reference lines are now plotted in the same colour as the actual plot line
* Fixed issue when navigating between inputs on filtered lists
* Fixed issue with missing history values for Test List cycles
* Added missing filter for "Assigned To" column on Test List listings
* The value 0 should no longer be shown in scientific notation
* Fixed issue with non linearly spaced graph data
* [various other issues](https://bitbucket.org/tohccmedphys/qatrackplus/issues?version=0.2.5&status=resolved&version=0.2.6)


### To upgrade from v0.2.5 ###

**Note: this release introduces some database shema changes.  BACK UP YOUR DATABASE
BEFORE ATTEMPTING THIS UPGRADE**

From the git bash shell in the root directory of your QATrack+ project

1. git pull origin master
1. python manage syncdb
1. python manage.py migrate
1. python manage.py collectstatic


## v0.2.5 ##

This release fixes some issues with control charts and makes test list pages
orderable and filterable.

There are no database schema changes in this release so updating should just
be a matter of pulling the latest release from git.

Changes in this release include:

* A number of improvments to the control chart functionality have been made
* Test lists and completed sessions are now sortable & filterable without a page refresh.
* On the overview page, you cannow collapse/expand the Units so that you can review one Unit at a time.
* Scientific notation is now used to display composite test results for large & small values.
* The behaviour when determining whether a value exactly on a pass/tolerance or tolerance/fail border has been improved (see [https://bitbucket.org/randlet/qatrack/issue/207/](issue 207))
* numpy & scipy are now available in the composite calculation context
* All test variable names (whether they have values entered for them or not) are now included in the composite calculation context.
* Crash in admin when "saving as new" with missing tests has been fixed.
* default work completed date is now an hour later than default work started.
* Fixed display of work completed date for last session details (time zone issue)
* Some other bug fixes and cleanup

## v0.2.4 ##

This release introduces [South](http://south.aeracode.org/) for managing
database schema migrations.  In order to update an existing database, you need
to do the following:

1. pip install south
2. *checkout version 0.2.4 code (e.g. git pull origin master)*
3. python manage.py syncdb
4. python manage.py migrate qa 0001 --fake
5. python manage.py migrate units 0001 --fake
6. python manage.py migrate qa

#### New Features ####

* added South migrations
* added description field to TestInstance Status models (displayed in tooltips when reviewing qa)
* Added new review page for displaying Test Lists by due date
* Added new review page for displaying overall QA Program status


#### Bug Fixes and Clean Up

* removed [salmonella](https://github.com/lincolnloop/django-salmonella) urls from urls.py


## v0.2.3 ##

This release has a number of small features and bug fixes included.

#### New Features ####

* Greatly improved permissions system.  Group/user specific permissions are no longer only controlled by the is_staff flag
* TestListCycle's now display the last day done
* You can now delete TestListInstances from the admin interface or when reviewing (redirects to admin)
* Cleaned up interface for choosing a unit a bit.


#### Bug Fixes ####

* Fixed js null bug when charting (see [issue #189](https://bitbucket.org/randlet/qatrack/issue/189/js-exception-on-generate-chart))
* Fixed expiring cookie issue that could potentially [cause QA data to be lost when submitted](https://bitbucket.org/randlet/qatrack/issue/178/possible-data-loss-if-user-is-logged-out).
* Deleting a UnitTestCollection no longer causes a server fault.
* [more](https://bitbucket.org/randlet/qatrack/issues?milestone=0.2.3)


## Release Checklist ##

* run pyflakes and fix errors
* run pep8 and fix errors
* grep for any print statements in py files
* grep for any pdb statements in py files
* grep for any console statements in js files
* Run test suite one last time :)
* Bump version number
* Update README.md with latest version number
* Ad-hoc testing
    * Perform test list with all types of tests including comments and skipped tests
    * Review test list
    * chart data
    * configure new test list
    * assign test list to unit with & without assigned frequencies
    * mark some data as invalid and confirm the due date is reset correctly
    * syncdb/migrate a newly created database
    * create fresh virtualenv and test 'pip install -r requirements/base.txt; pip install -r requirements/optional.txt' then run test suite.
* Release notes
    * include upgrade commands
    * don't forget changes to requirements
* Update wiki



