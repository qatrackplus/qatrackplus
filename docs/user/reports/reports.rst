.. _reports-reports:

Reports
=======

As of version 0.3.1 QATrack+ has a tool for generating and scheduling reports
in PDF/Excel/CSV formats.  To access the tool, select the **Reports** option
from the `Trends & Analysis` menu.

Permissions Required
--------------------

Generating reports requires a user to have the :ref:`"Can Run Reports" or "Can
Create Reports" <qa_auth>` permission set on their account.

.. _reports-available:

Available Report Types
----------------------

The report types currently available in QATrack+ are:

* General:

    * :ref:`QC Summary <reports-qc_summary>`: This report lists all Test List
      Instances from a given time period for selected sites, units,
      frequencies, and groups.

    * :ref:`Test List Instances <reports-tlis>`: This report includes details for all Test List
      Instances from a given time period for a given Unit Test List (Cycle)
      assignment.

    * :ref:`Test Instance Values <reports-tis>`: This report shows QC test
      values for select tests/units.

* Scheduling:

    * :ref:`Next Due Dates for QC <reports-next_due>`: This report shows QC
      tests whose next due date fall in the selected time period.

    * :ref:`Due and Overdue QC <reports-due_overdue>`: This report shows QC
      tests which are currently due or overdue


If there are other reports you would like to see please file an issue For
custom reporting please submit an `issue on BitBucket
<https://bitbucket.org/tohccmedphys/qatrackplus/issues/>`_.


Creating a New Report
---------------------

On the left hand side of the page you will find the `Report Configuration` area:

.. figure:: images/config.png
   :alt: Configuration options for a new report.

   Configuration options for a new report.

The fields in this are as follows:

Currently editing / Clear Report / Delete Report:
    This field will display `New Report` when creating a new report, or the
    name of the saved report currently being edited.

    In order to clear the current report, click the `X` button to the right
    of the `Currently editing` field.

    In order to delete the current report, click the trash can button to the
    right of the `Currently editing` field.  A popup will be displayed asking
    you to confirm the deletion.

Title
    Give your report a descripitive title

Report Type
    Select the :ref:`Report Type <reports-available>` you wish to generate.

Report Format
    Select the format you would like your report to be generated as.  Most
    reports are available as PDF, CSV, or Excel however, some may only be
    available in a subset of these formats (e.g. the :ref:`Test Instance Values
    <reports-tis>` is only available in CSV/Excel formats.

Visible To
    When you save a report, you can optionally choose to have that report
    :ref:`visible to others <reports-loading>`.  Select the groups you want to
    share your report with in this field, or leave blank to keep the report
    private.

Signature
    If you check this option, there will be a placeholder for a signature and
    the current date included at the end of PDF reports.


.. _reports-filters:

Report Filters
--------------

Most of the reports have either optional or required filters which you can
apply before generating a preview or downloading your report. Please see the
individual :ref:`report descriptions <reports-descriptions>` for explanations
about what filters are available on each report.


.. _reports-saving:

Previewing, Saving, or Downloading a Report
-------------------------------------------

Underneath the `Report Filters` section are buttons for saving, downloading, and
previewing your report.

.. figure:: images/buttons.png
   :alt: Buttons for dowloading, saving, or previewing a report.

   Buttons for dowloading, saving, or previewing a report.

Once you have set up the filters required for your report, you can generate an
online preview (only available for reports which have a PDF `Report format`
option.). You can generate an online preview of your report by clicking the
`Preview` button.  The report will be generated on the QATrack+ server and then
displayed for you in the `Report Preview` area.

Clicking the `Download` button will allow you to download the report in your
desired format, while clicking the `Save` button will add this report to your
saved reports which are available for future use in the `Saved & Scheduled
Reports` section on the right hand side of the Reports page.

.. _reports-loading:

Loading a Saved Report
----------------------

On the right hand side of the screen on the Reports page you will find the
`Saved & Scheduled Reports` section which contains a table of all your
previously saved reports:

.. figure:: images/saved.png
   :alt: Saved & Scheduled Reports area

   Saved & Scheduled Reports area

To load a previously saved report, click on the title link of the report in the
`Report` column of the table.  The report will then be loaded and you can
preview it, download it, or edit its configuration and save it again.

.. _reports-scheduling:

Scheduling a Report
-------------------

In order to schedule a report for delivery you first need to :ref:`Save
<reports-saving>` it.  Then, in the `Saved & Scheduled Reports` area, click
the calendar icon beside the report you want to schedule:

.. figure:: images/schedule-icon.png
   :alt: Click the calendar icon to schedule your report.

   Click the calendar icon to schedule your report.

This will bring up a dialogue with a scheduling form for you to fill out. The
fields in this form are as follows:

Schedule (required)
    Set a recurrence rule for the days that you would like your report sent.

Time of Day (required)
    Set the time of day you would like the report emailed.

Groups (optional)
    If you want the report delivered to one or more user groups, select those
    here.

Users (optional)
    To have the report delivered to individual users, select them here

Extra recipient emails (optional)
    Add any additional emails you would like this report sent to.


Once you have set the schedule and recipients, click the `Update Schedule`
button and then click `Close`.

.. figure:: images/schedule.png
   :alt: Setting the schedule and recipients for a report.

   Setting the schedule and recipients for a report.

Editing or Clearing the Schedule and/or recipients for a Report
...............................................................

To edit or clear the schedule for a report, click on the `Edit Calendar`
icon next to your report.

.. figure:: images/edit-schedule.png
   :alt: Click the edit calendar icon to schedule your report.

   Click the edit calendar icon to schedule your report.

You can then adjust the recipients and/or schedule for your report and click
`Update Schedule` and then `Close`.

To clear the schedule for a report open the scheduling dialogue and click the
`Clear Schedule` button and then click `Close`.

.. _reports-delete:

Deleting a Saved Report
-----------------------

In order to delete a saved report, first :ref:`load <reports-loading>` the
report then click the trash can icon next to the `Currently Editing` field:

.. figure:: images/delete.png
   :alt: Click the trash can icon to delete your report.

   Click the trash can icon to delete your report.

.. _reports-descriptions:

Report Type Descriptions & Options
----------------------------------

General
.......

.. _reports-qc_summary:

QC Summary
^^^^^^^^^^

.. figure:: images/qcsummary.png
   :alt: An example QC Summary report

   An example QC Summary report

This report tabulates all completed Test List Instances from a given time
period for selected sites, units, frequencies, and groups.

The filters available for this report are:

Work Completed (required)
    Select the period you want to include Test List Instances from.

Site (optional)
    Filter your results to one or more :ref:`Site <unit_site>`'s, you can
    select them here.

Unit (optional)
    Filter your results to one or more :ref:`Unit <units_admin>`'s, you can
    select them here.

Frequency (optional)
    Filter your results to those scheduled with a specific :ref:`frequency
    <qa_frequencies>` (e.g. Monthly).

Assigned To (optional)
    Filter your results to those assigned to a specific :ref:`group <auth_groups>`.


.. _reports-tlis:

Test List Instances
^^^^^^^^^^^^^^^^^^^

.. figure:: images/tlis.png
   :alt: An example Test List Instance report

   An example Test List Instance report

This report includes details for all Test List Instances from a given time
period for a given Unit Test List (Cycle) assignment.

The filters available for this report are:

Work Completed (required)
    Select the period you want to include Test List Instances from.

Test List (Cycle) Assignment (required)
    Select the Test List Unit Assignments that you want to include in this report.


.. _reports-tis:

Test Instance Values (Excel/CSV only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. figure:: images/tis.png
   :alt: An example Test Instance Value report

   An example Test Instance Value report

This report shows QC test values for selected tests/units.

The filters available for this report are:

Work Completed (required)
    Select the period you want to include Test values from

Test (required)
    Select the test you want to generate a report for

Site (optional)
    Filter your results to one or more :ref:`Site <unit_site>`'s, you can
    select them here.

Unit (optional)
    Filter your results to one or more :ref:`Unit <units_admin>`'s, you can
    select them here.

Organization (required)
    Select how you want your results organized.

    * One Test Instance Per Row:  Only include a single value per row in the
      spreadsheet
    * Group rows by tests that are performed on the same unit, on the same
      date.



Scheduling
..........

.. _reports-next_due:

Next Due Dates for QC
^^^^^^^^^^^^^^^^^^^^^

.. figure:: images/nextduedates.png
   :alt: An example Next Due Dates report

   An example Next Due Dates report

This report shows QC tests whose next due date fall in the selected (future)
time period.

The filters available for this report are:

Time Period (required)
    Select the period you want to include due dates for.

Assigned To (optional)
    Filter your results to those assigned to a specific :ref:`group <auth_groups>`.

Site (optional)
    Filter your results to one or more :ref:`Site <unit_site>`'s, you can
    select them here.

Unit (optional)
    Filter your results to one or more :ref:`Unit <units_admin>`'s, you can
    select them here.


.. _reports-due_overdue:

Due and Overdue
^^^^^^^^^^^^^^^

.. figure:: images/dueoverdue.png
   :alt: An example Due & Overdue report

   An example Due & Overdue report

This report shows QC tests which are currently due and overdue.

The filters available for this report are:

Assigned To (optional)
    Filter your results to those assigned to a specific :ref:`group <auth_groups>`.

Site (optional)
    Filter your results to one or more :ref:`Site <unit_site>`'s, you can
    select them here.

Unit (optional)
    Filter your results to one or more :ref:`Unit <units_admin>`'s, you can
    select them here.

