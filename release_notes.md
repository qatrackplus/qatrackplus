# QATrack+ Release Notes

## v0.2.6
This release does

Requires migrate qa to add new permission "Can skip without comment" and make
256 column widths to be 255.

### To upgrade from v0.2.5

**Note: this release introduces some database shema changes.  BACK UP YOUR DATABASE
BEFORE ATTEMPTING THIS UPGRADE**

1. Check out latest version from git (e.g. git pull origin master)
2. python manage syncdb
3. python manage.py migrate qa


## v0.2.5

This release fixes some issues with control charts and makes test list pages
orderable and filterable.

There are no database schema changes in this release so updating should just
be a matter of pulling the latest release from git.

Changes in this release include:

* A number of improvments to the control chart functionality have been made
* Test lists and completed sessions are now sortable & filterable without a page refresh.
* On the overview page, you cannow collapse/expand the units so that you can review one unit at a time.
* Scientific notation is now used to display composite test results for large & small values.
* The behaviour when determining whether a value exactly on a pass/tolerance or tolerance/fail border has been improved (see [https://bitbucket.org/randlet/qatrack/issue/207/](issue 207))
* numpy & scipy are now available in the composite calculation context
* All test variable names (whether they have values entered for them or not) are now included in the composite calculation context.
* Crash in admin when "saving as new" with missing tests has been fixed.
* default work completed date is now an hour later than default work started.
* Fixed display of work completed date for last session details (time zone issue)
* Some other bug fixes and cleanup

## v0.2.4

This release introduces [South](http://south.aeracode.org/) for managing
database schema migrations.  In order to update an existing database, you need
to do the following:

1. pip install south
2. *checkout version 0.2.4 code (e.g. git pull origin master)*
3. python manage.py syncdb
4. python manage.py migrate qa 0001 --fake
5. python manage.py migrate units 0001 --fake
6. python manage.py migrate qa

#### New Features

* added South migrations
* added description field to TestInstance Status models (displayed in tooltips when reviewing qa)
* Added new review page for displaying Test Lists by due date
* Added new review page for displaying overall QA Program status


#### Bug Fixes and Clean Up

* removed [salmonella](https://github.com/lincolnloop/django-salmonella) urls from urls.py


## v0.2.3

This release has a number of small features and bug fixes included.

#### New Features

* Greatly improved permissions system.  Group/user specific permissions are no longer only controlled by the is_staff flag
* TestListCycle's now display the last day done
* You can now delete TestListInstances from the admin interface or when reviewing (redirects to admin)
* Cleaned up interface for choosing a unit a bit.


#### Bug Fixes

* Fixed js null bug when charting (see [issue #189](https://bitbucket.org/randlet/qatrack/issue/189/js-exception-on-generate-chart))
* Fixed expiring cookie issue that could potentially [cause QA data to be lost when submitted](https://bitbucket.org/randlet/qatrack/issue/178/possible-data-loss-if-user-is-logged-out).
* Deleting a UnitTestCollection no longer causes a server fault.
* [more](https://bitbucket.org/randlet/qatrack/issues?milestone=0.2.3)



