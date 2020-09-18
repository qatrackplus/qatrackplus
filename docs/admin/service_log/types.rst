.. _sl_service_type:

Service Types
=============

Every Service Event initiated needs to have a `Service Type` associated with
it.

To create `Service Types` :ref:`go to the Admin section <access_admin_site>`
and click the `Service Types` link in the `Service Log` section and then click
the `Add Service Type` button.  Fill in the fields as follows:

* **Name** A short descriptive name for the Service Type.
* **Is review required** This flag controls whether the "Is Review Required"
  checkbox is enabled when entering/editing service events.  If this flag is 
  not checked, then users will have the option of not requiring a new Service Event
  to be reviewed.  If this flag is checked, then all Service Events of this type
  will be required to undergo review.  For example, you may wish to leave
  this flag unchecked for minor service types and allow the person entering
  the service event details to determine whether it needs to be reviewed or not. Conversely
  you may want to check this flag for extensive, or safety systems service types.
* **Is active**  Unchecking this will hide the Service Type from drop down menus
* **Description** A brief description of this service type


By default the following Service Types are defined:


.. list-table::
    :header-rows: 1
    :widths: 20 20 60

    * - Service Type
      - Requires Approval
      - Definition

    * - Preventive (Regular) Maintenance
      - No
      - Anything that is recommended by the manufacturer for routine (e.g.
        daily, weekly, monthly, quarterly and annual) maintenance and is on a
        schedule.

    * - Minor Repairs / Corrective Maintenance
      - No
      - Anything that is not part of a routine schedule and requires
        intervention without parts replacement.

    * - Extensive Repairs
      - No
      - Any repair that is not part of a routine schedule and involves the
        replacement of parts.  In addition, any action that involves changes to
        ANY operating parameter (i.e. steering coils, gun current, readout
        calibration, etc.).

    * - Safety Systems
      - Yes
      - Any repair that involves a CNSC regulated safety system. Examples are
        in-room monitors, room interlocks, prim alert, etc

