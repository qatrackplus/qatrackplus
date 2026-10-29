.. _dev_schema:

QATrack+ Database Schema
=========================

Below you will find the most recent database schema diagram generated for
QATrack+ (v4.0). Older v3.1.0 and v0.3.0 diagrams are also kept for
reference, further down this page.

The diagram is named for the minor line rather than a specific patch release,
because the models are the same across every 4.0.z.

.. figure:: images/qatrack_schema_4.0.svg
   :alt: QATrack+ v4.0 schema

   The QATrack+ v4.0 schema (click to view full size or right click and view
   in new tab to view full size)

This diagram is regenerated on demand (see *Generating the schema diagram*
below) rather than on every release, so it may lag behind the current
version - regenerate it if you need one that reflects the latest models.


Generating the schema diagram
-----------------------------


Ubuntu
~~~~~~

On Ubuntu 24.04 LTS you need to install a few dependencies before generating the
schema diagram:

.. code-block:: sh

    sudo apt install python3-dev graphviz libgraphviz-dev pkg-config
    uv pip install pygraphviz

and then you can generate your schema with:

.. code-block:: sh

    make schema

which will output the schema to
``docs/developer/images/qatrack_schema_<major>.<minor>.svg`` - for example
``qatrack_schema_4.0.svg``. The version comes from the installed package, and the
diagram is named for the minor line rather than the patch release because the
schema is the same across every patch of a line: a change to it needs a
migration, which makes it a minor release.

``poe schema`` does the same thing without Make.

The output is gitignored. Running either command to *look* at the schema will not
stage an 838 KB SVG into an unrelated branch; adding the diagram for a new minor
line is a deliberate ``git add -f``.


Windows
~~~~~~~

It is also possible to generate a schema diagram on Windows using Sql Server
Management Studio. See
https://dataedo.com/kb/tools/ssms/create-database-diagram for instructions on
making a diagram with SSMS.


Schema for Older Versions
=========================

.. figure:: images/qatrack_schema_3.1.0.svg
   :alt: QATrack+ v3.1.0 schema

   The QATrack+ v3.1.0 schema (click to view full size or right click and view
   in new tab to view full size)

.. figure:: images/qatrack_schema_0.3.0.svg
   :alt: QATrack+ v0.3.0 schema

   The QATrack+ v0.3.0 schema (click to view full size or right click and view
   in new tab to view full size)

Database diagrams for even older versions of QATrack+ are available on
BitBucket: `Schema diagrams
<https://bitbucket.org/tohccmedphys/qatrackplus/wiki/v/0.2.9/developers/schema.md>`__.
