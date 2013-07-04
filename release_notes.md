# QATrack+ Release Notes #

## v0.2.7 ##

* upgrade django-regisration
* AD logging
* assign composite values with macro name instead of result
* upload test type
* string test type
* qa/views.py refactored into qa/views/\*.py
* page load time reduced by using more efficient unreviewed count query
* charts page now allows plotting of data for tests which are no longer active

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
* Release notes
    * include upgrade commands
    * don't forget changes to requirements
* Update wiki



