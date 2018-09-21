.. _sl_service_type:

Service Types
=============

Every Service Event initiated needs to have a `Service Type` associated with
it.

To create `Service Types` :ref:`go to the Admin section <access_admin_site>`
and click the `Service Types` link in the `Service Log` section and then click
the `Add Service Type` button.  Fill in the fields as follows:

* **Name** A short descriptive name for the Service Type.
* **Is review required** Indicate whether this service type requires review
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

