Units
=====

Creating A New Unit
-------------------

Before you can create a new unit you have to define some modalities and
unit types. This can either be done on beforehand or "inline" when
defining a new unit. The former is described below.

Defining a modality
-------------------

*Note that in the future the modality types will be replaced by a simple
text input field so modalities will no longer be confined to only those
associated with radiation therapy machines (i.e. so we can have
modalities like ultrasound or pet).*

From the main administrators page click the **Modalities** link from the
**Units** section.

.. figure:: images/units_admin.png
   :alt: Units admin section

   Units admin section

This page lists all the existing (if any) modalities. To add a new
modality click the **Add modality** button at the top right.

.. figure:: images/add_modality.png
   :alt: Add Modality

   Add Modality

From here choose whether you want to define a photon or electron
modality and the energy of the beam. The definition of a 6MV photon beam
is illustrated below.

.. figure:: images/modality.png
   :alt: Defining a 6MV Photon Modality

   Defining a 6MV Photon Modality

Click **Save** when you are finished.

Defining a new unit type
------------------------

From the main administrators page click the **Unit Types** link from the
**Units** section and then on the next page click the **Add unit type**
link in the top right hand corner.

Fill in the **Name**, **Vendor** and optional **Model** fields and click
**Save** when you are finished.

.. figure:: images/unit_type.png
   :alt: Defining a new unit type

   Defining a new unit type

Defining a new unit
-------------------

From the main administrators page click the **Units** link from the
**Units** section and then on the next page click the **Add unit** link
in the top right hand corner.

Fill in the **Number**, **Name**, and optional **Serial number**,
**Location** and **Install date** fields. Note that the **Number** must
be a uniquely identifying integer number for this unit. The unit
**Number** will effect the order that treatment units are displayed on
certain pages.

Next select the unit type from the dropdown list. You can use a
previously defined unit type or add a new type by clicking the green
cross located next to the dropdown.

Finally, choose the modalities available on this unit by selecting the
desired modalities and moving them from the *Available modalities* to
the *Chosen modalities* box by selecting them and using the right and
left arrows between the two boxes.

Example input for an Elekta Synergy unit is shown below.

.. figure:: images/new_unit.png
   :alt: Defining a new unit type

   Defining a new unit type
