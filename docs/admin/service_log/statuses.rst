.. _sl_statuses:

Service Event Statuses
======================

Similar to :ref:`Test Instance Status's <qa_statuses>`, :term:`Service Event`\s
have a status associated with them.  These Service Event Status help manage the
flow of a Service Event from initiation to completion.

To create `Service Event Statuses` :ref:`go to the Admin section
<access_admin_site>` and click the `Service Event Statuses` link in the
`Service Log` section and then click the `Add Service Event Status` button.
Fill in the fields as follows:

* **Name** A short descriptive name for the status

* **Is default** Check off whether this should be considered the default
  Service Event Status when initiating a Service Event.

* **Is review required**  Do service events with this status require review?

* **RTS qa review required**  Service events with Return To Service (RTS) QC
  that has not been reviewed can not have this status selected if set to true.
  For example, you may have an `Approved` Service Event Status that requires
  one or more Test Lists to be performed *and* approved before the Service
  Event can have its status set to `Approved`.

* **Description** A description of this status

* **Color** Service Event Statuses can have different colours associated with them.


Examples
--------

By default the following Service Event Statuses are configured:

.. list-table::
    :header-rows: 1

    * - Status Name
      - Is Review Required
      - Is Default
      - RTS QC Must be reviewed
    * - Service Pending
      - Yes
      - No
      - No
    * - Service In Progress
      - Yes
      - Yes
      - No
    * - Service Complete
      - Yes
      - No
      - No
    * - Approved
      - No
      - No
      - Yes
    * - Test Data
      - No
      - No
      - No
    * - Rejected
      - No
      - No
      - No

