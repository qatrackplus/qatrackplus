# QATrack+
###### Copyright 2012 The Ottawa Hospital Cancer Center

---

QATrack+ is a fully configurable, free, and open source (MIT License) web application that is deployable on
most operating system/server/database platform combinations. It was developed in the popular
Python programming language using the Django web framework so that QC data may be
entered, reviewed, and analyzed using a web browser.

Take a look at the [screenshots](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/screenshots) to get
an idea of the interface.

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

---

## Documentation & Release Notes

The latest version is 0.2.8 Please review the [release_notes](https://bitbucket.org/tohccmedphys/qatrackplus/src/master/release_notes.md) before
installing or upgrading.

The [documentation can be found
online](https://bitbucket.org/tohccmedphys/qatrackplus/wiki/Home) and is where you
should start if you
are interested in installing or helping develop QATrack+.

---

## Important notes regarding 3rd party code in QATrack+

QATrack+ relies on a number of open source projects, a few of which are
distributed along with QATrack+; licenses covering their usage and
modification are either included along with the source code files or embeded
directly in the source (or a url where you can find it).

### Highcharts ###

QATrack+ is distributed with the excellent
[HighStock](http://www.highcharts.com/products/highstock) charting library.
Highstock is free for personal & non-profit sites but is NOT free for
commercial use. Please see the [HighStock license
page](http://shop.highsoft.com/highstock.html#redist) for details.


### Bootstrap & Glyphicons ###

For look and feel QATrack+ uses the [Bootstrap](http://getbootstrap.com) html/js/css framework which
comes with [Glyphicons](http://glyphicons.com/license/).

### FontAwesome ###

Most of the icons in QATrack+ are provided by [Font Awesome]( http://fortawesome.github.io/Font-Awesome/icons/).

### jQuery ###

The ubiquitous javscript library: [jQuery](http://jquery.com)

### Lo-Dash ###

A javascript utility library [Lo Dash](http://lodash.com/)

### Data Tables ###

[Data Tables](http://www.datatables.net/) is an excellent table plugin for jQuery.

### jQuery File Upload Plugin ###

[A plugin](https://github.com/blueimp/jQuery-File-Upload) for doing ajax uplods with jQuery.




