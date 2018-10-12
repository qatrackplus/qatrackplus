# QATrack+
###### Copyright 2012 The Ottawa Hospital Cancer Center
---

![build badge](https://travis-ci.org/randlet/qatrackplus-ci.svg?branch=master)


QATrack+ is a fully configurable, free, and open source (MIT License) web
application for managing QA data for radiation therapy and medical imaging
equipment. QATrack+ is now used in many hospitals and clinics [around the
world](http://qatrackplus.com/#whos-using)! Visit the QATrack+ homepage at
http://qatrackplus.com

QATrack+ is deployable on most operating system/server/database platform
combinations. It was developed in the popular Python programming language using
the Django web framework so that QC data may be entered, reviewed, and analyzed
using a web browser.

The main features include:

* Ability to define QC tests via an user-friendly interface. Configuration
  settings are available for data type (Boolean, float, computational result,
  or multiple choice selection), test frequency (due/past due dates), reference
  values, and tolerance and action levels. Test configurations can be grouped
  and assigned to multiple units/devices to reduce configuration workload, and
  to simplify the configuration maintenance.
* Several options for trending numerical data via control charts and other
  tools. Data can be filtered by unit, date, or frequency, and can also be
  exported for external analysis.
* Support for multiple, unique user groups (e.g. administrators, physicists,
  assistants, therapists, etc) with user & group-specific privileges and test
  lists, as well as a configurable user authentication system.
* Easily integrate test procedures into data entry forms via embedded html
  or links to external documentation.
* Save incomplete work and complete it a later date.
* Configure a review/approval process with additional options for
  classifying data. The software also allows reviewers to easily differentiate
  between measurements performed as part of investigative work, or as part of
  routine QC testing.
* Integrated Service Log for tracking service events and machine downtime
* Parts tracker for tracking spare parts on hand, part costs and vendors
* Optional and configurable email notifications.
* The flexibility to host on an intranet or www, requiring minimal resources
  from IT departments. Can optionally be managed within a physics department if
  permitted by local institution policies.


## Documentation & Release Notes

The latest version is 0.3.0 Please review the
[release_notes](https://docs.qatrackplus.com/en/latest/release_notes.html)
before installing or upgrading.

The [documentation for versions 0.3.0+ can be found online](http://docs.qatrackplus.com)
and is where you should start if you are interested in installing or helping
develop QATrack+.

Documentation for earlier versions of QATrack+ (v0.2.7-v0.2.9) can be found in
the [QATrack+ Wiki on BitBucket](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/Home).

---

## Important notes regarding 3rd party code in QATrack+

QATrack+ relies on a number of open source projects, many of which are
distributed along with QATrack+; licenses covering their usage and modification
are either included along with the source code files or embeded directly in the
source (or a url where you can find it).
