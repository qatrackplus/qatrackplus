.. QATrack+ documentation master file, created by
   sphinx-quickstart on Mon Jun  4 22:03:51 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to QATrack+'s documentation!
====================================


About QATrack+
--------------

QATrack+ is a fully configurable, free, and open source (MIT License) web
application for managing QA data for radiation therapy and medical imaging
equipment. QATrack+ is now used in many hospitals and clinics around the world!
Visit the QATrack+ homepage at http://qatrackplus.com

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


Documentation for QATrack+ v0.2.7-v0.2.9
========================================

As of version 0.3.0 QATrack+ documentation is hosted at
http://docs.qatrackplus.com. For versions prior to v0.3.0, please see the
`QATrack+ Wiki on BitBucket
<https://bitbucket.org/tohccmedphys/qatrackplus/wiki/>`__.



Problems, Questions or Suggestions?
===================================


Bugs or Feature Requests
------------------------

If you have a bug to report or a feature to request please use the
:issues:`BitBucket Issues <>` page.

Mailing List, General Questions, Discussions or Support?
--------------------------------------------------------

If you have general questions, want to have an initial discussion about
features or the way things work (basically anything that isn't a specific bug
report or feature request) please use the :mailinglist:`Google QATrack+ Group
Forum <>`.

This forum is also a mailing list and it is highly recommended that you
subscribe to email updates from the forum to get all the announcements about
QATrack+ releases and discussions.

Commercial Support and Hosting Services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Commercial support and cloud hosting services for QATrack+ are now available
from `Multi Leaf Consulting <https://multileaf.ca>`__.

Email
-----

Want to discuss something directly with the QATrack+ team?  Please feel free to
email directly:

* Randy Taylor (QATrack+ lead developer): randy@multileaf.ca
* Crystal Angers (TOHCC QATrack+ lead): cangers@toh.ca
* Ryan Bottema (TOHCC QATrack+ developer): rbottema@toh.ca


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   self
   glossary
   release_notes
   install/install
   admin/guide
   user/guide
   api/guide
   developer/guide
   tutorials/index
   screenshots


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
