# QATrack+
###### Copyright 2012 The Ottawa Hospital Cancer Center

---

QATrack+ is a fully configurable, free, and open source (MIT License) web application that is deployable on
most operating system/server/database platform combinations. It was developed in the popular
Python programming language using the Django web framework so that QC data may be
entered, reviewed, and analyzed using a web browser.

The main features include:

* ability to define QC tests via an user-friendly interface. Configuration settings are
available for data type (Boolean, float, computational result, or multiple choice
selection), test frequency (due/past due dates), reference values, and tolerance and action
levels. Test configurations can be grouped and assigned to multiple units/devices to
reduce configuration workload, and to simplify the configuration maintenance.
* several options for trending numerical data via control charts and other tools. Data can be
filtered by unit, date, or frequency, and can also be exported for external analysis.
* support for multiple, unique user groups (e.g. administrators, physicists, assistants,
therapists, etc) with user & group-specific privileges and test lists, as well as a configurable user
authentication system.
* ability to integrate test procedures into data entry forms via embedded html or links to
external documentation.
* ability to save incomplete work.
* ability to configure a review/approval process with additional options for classifying data.
The software also allows reviewers to easily differentiate between measurements
performed as part of investigative work, or as part of routine QC testing.
* optional and configurable email notification.
* the flexibility to host on an intranet or www, requiring minimal resources from IT
departments. Can optionally be managed within a physics department if permitted by
local institution policies.

## Documentation & Release Notes

The latest version is 0.2.4 Please review the [release_notes](https://bitbucket.org/randlet/qatrack/src/master/release_notes.md) before
installing or upgrading.

The [documentation can be found
online](https://bitbucket.org/randlet/qatrack/wiki/Home) and is where you
should start if you
are interested in installing or helping develop QATrack+.

## Important notes regarding 3rd party code in QATrack+

QATrack+ is distributed with the excellent
[HighStock](http://www.highcharts.com/products/highstock) charting library.
Highstock is free for personal & non-profit sites but is NOT free for
commercial use. Please see the [HighStock license
page](http://shop.highsoft.com/highstock.html#redist) for details.

A number of other 3rd party libraries are distributed with QATrack+ and
licenses covering their usage and modification have been included along with
the source code.

