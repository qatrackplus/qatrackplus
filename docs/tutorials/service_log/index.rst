.. _tutorial_service_log:

A Complete Service Log Example
==============================

In this tutorial we will walk through a complete example of using Service Log
to record an output adjustment that is made after morning QC revealed that the
output was too high.

Scenario
--------

The output on a unit has been trending upwards for a little while and one
morning the morning output check indicates that the machine output is outside
of action levels and treatment can not begin:


.. figure:: images/output_high.png
    :alt: Output is outside of action levels

    Output is outside of action levels

The therapist measuring output uses the QATrack+ contacts information to call the
on on-call physcist and informs them of the issue:


.. figure:: images/contacts.png
    :alt: Contacts displayed while performing QC

    Contacts displayed while performing QC

The physicist must now restrict the machine and perform an output adjustment
working alongside the field service engineer (FSE).

Resolution
----------

The physicist opens QATrack+ and visits the `Enter new Service Event` page:


.. figure:: images/new_service_event_menu.png
    :alt: The New Service Event Menu

    The New Service Event Menu

The physicist then enters the basic information about this service event:


.. figure:: images/service_event_basic_fields.png
    :alt: Basic information about the Service Event

    Basic information about the Service Event

and then, since this SE was related to a specific :term:`Test List Instance`,
they choose the related Test List, and specific Test List Instance from the
`Initiated By` drop down menu and popup:


.. figure:: images/initiated_by.png
    :alt: Selecting Initiated By Test List

    Selecting Initiated By Test List


.. figure:: images/initiated_by_popup.png
    :alt: Selecting Initiated By Test List Instance

    Selecting Initiated By Test List Instance


.. figure:: images/initiated_by_selected.png
    :alt: Selected Initiated By Test List Instance

    Selected Initiated By Test List Instance


Since the service will be performed, now, the physicist changes the Service
Status to  `Service In Progress`:


.. figure:: images/in_progress.png
    :alt: Service In Progress status

    Service In Progress status


Next the physicist selects the Return To Service QC that will be required before
the Unit can be released for clinical duty:


.. figure:: images/rtsqa_selected.png
    :alt: Return To Service QC Selected

    Return To Service QC Selected

The physicist now clicks `Save` and the are ready to make the output
adjustment. Note that the Service Log Dashboard will now show 1 incomplete
:term:`Return to Service QC` and 1 Service Event needing review.


.. figure:: images/dash.png
    :alt: Service log dashboard

    Service log dashboard



After The Adjustment
--------------------

The physicist and FSE have now made the adjustment and will now, perform the
Return to Service QC. The physicist clicks the  `Incomplete Return To Service QC` button (shown above)
and then clicks `Perform` next to the RTS QC list item:


.. figure:: images/rtsqa_list.png
    :alt: Return To Service QC Listing

    Return To Service QC Listing

After the RTSQC is performed the physicist returns to Edit the Service Event so
they can complete the entry of how much time it took and who was involved:


.. figure:: images/service_event_edit.png
    :alt: Edit Service Event Button

    Edit Service Event Button


The `Work description`, `Service Event Durations`, `Group Members Involved` and
`User and Third Party Work Durations` fields can now all be filled out (If any
parts were used in the Service Event, this would also be the time to enter
them):


.. figure:: images/service_event_completed_fields.png
    :alt: Fields filled out after Service Event is completed

    Fields filled out after Service Event is completed

The `Service Event Status` can now be set to `Service Complete`:

.. figure:: images/service_complete.png
    :alt: Service completed status

    Service completed status

and `Save`'d again.

The Dashboard will now show that there is one Return To Service QC, and 1
Service Event awaiting review:


.. figure:: images/dash_after_rts.png
    :alt: Dashboard after Return To Service QC

    Dashboard after Return To Service QC


Reviewing The RTSQC and Service Event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The physicist now goes back to the `Edit` page for the Service Event. Note that
an attempt to save the Service Event with the Service Event Status to
`Approved` before the RTSQC has been approved will result in an error!


.. figure:: images/cant_approve_yet.png
    :alt: Can't approve a Service Event without reviewing the RTS QC first

    Can't approve a Service Event without reviewing the RTS QC first

Instead, the physicist first clicks through the `Review` link for the RTSQC and
:ref:`reviews <qa_review>` the QC:


.. figure:: images/review_link.png
    :alt: Review RTSQC Link

    Review RTSQC Link

after the RTSQC Test List Instance is reviewed, the physicist is directed back
to the `Edit` page for the Service Event where you can see the updated `Review
Status` of the RTSQC:



.. figure:: images/all_reviewed.png
    :alt: All RTS QC reviewed

    All RTS QC reviewed

The Service Event Status can now be set to `Approved` and this Service Event is
now complete!


.. figure:: images/approved.png
    :alt: Service Event Approved

    Service Event Approved



.. figure:: images/all_done.png
    :alt: Dashboard after Service Event reviewed and approved

    Dashboard after Service Event reviewed and approved

