Welcome to QATrack+'s documentation!
====================================


About QATrack+ v3.1.0
---------------------

QATrack+ is a fully configurable, free, and open source (MIT License) web
application for managing QC data for radiation therapy and medical imaging
equipment. QATrack+ is used in `many hospitals and clinics around the world
<http://qatrackplus.com/#whos-using>`!

QATrack+ is a replacement for error prone spreadsheets and other in-house
databases. It brings structure and organization to your QA program while
retaining much of the flexibility of spreadsheets.  Built in scheduling,
reports, notifications, and charts make keeping on top of your machine QA
program a breeze!

The main features include:

* :ref:`Record <qa_perform>` & :ref:`review <qa_review>` your QC data via a
  user friendly web application.

* Fully customized QC tests.  You configure QATrack+ to record the data that is
  important to you.  QATrack+ comes with a number of :ref:`test types
  <qa_tests>` including:

    * numerical
    * text
    * file upload & analysis using Python scripts (arbitrary file types including DICOM, JPG, TIFF etc)
    * yes/no
    * multiple choice
    * calculations using Python snippets
    * date & times
    * and :ref:`more <qa_tests>`!

* Schedule your QC on a daily, weekly, monthly, semi-annual, annual or define
  your own custom scheduling recurrence rules.

* Configure :ref:`notifications <notifications>` to alert you when:

    * Scheduled QC tests are due or overdue
    * QC tests are completed
    * Service events are created
    * :ref:`more <notifications>`!

* Built in :ref:`data charts <qa_charts>` for trending numerical test results.
  Data can be filtered by unit, date, or frequency, and can also be exported
  for external analysis.

* :ref:`PDF & Excel reports <reports>` that can be generated on the fly, or
  delivered to you via email on a schedule of your choosing.

* Support for :ref:`multiple user groups <qa_auth>` (e.g. Administrators,
  Physicists, Assistants, Therapists, etc) with user & group-specific
  privileges and test lists, as well as a configurable user authentication
  system.

* Easily integrate test procedures into data entry forms via embedded html
  or links to external documentation.

* Save incomplete work and complete it a later date.

* Perform manual :ref:`review & approval <qa_review>` of QC data or use
  :ref:`Auto Review Rules <qa_auto_review>` to cut down your QC Review
  workload.

* Integrated :ref:`Service Log <service_log>` for tracking service events and
  machine downtime

* Parts tracker for tracking spare parts on hand, part costs and vendors

* The flexibility to host on an intranet or www, requiring minimal resources
  from IT departments. Can optionally be managed within a physics department if
  permitted by local institution policies.


Screenshots
-----------

For some example screenshots, please see the :ref:`screenshots` page.

Installation & Deployment
-------------------------

QATrack+ is deployable on most operating system/server/database platform
combinations. It was developed in the popular Python programming language using
the Django web framework so that QC data may be entered, reviewed, and analyzed
using a web browser.


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
:issues:`GitHub Issues <>` page.

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
