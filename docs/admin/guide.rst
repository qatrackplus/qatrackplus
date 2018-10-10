.. _admin_guide:

Administrators Guide
====================


Introduction
-----------------------

The admin guide is intended for use by anyone who will be responsible for
configuring tests and test lists, modifying references & tolerances or managing
users and user permissions.  Typically this would be limited to a small group
of users within the clinic.


.. _access_admin_site:

Accessing the admin site
------------------------

To access the admin site, log into QATrack+ and then choose the **Admin**
option from the dropdown at the top right hand corner of the page (where your
username is displayed).

A walk through tutorial (with screenshots) on going from a blank QATrack+
install to a fully configured, performable test list is available on the
`Tutorials page <../tutorials/index.rst>`__.  Reading through this tutorial is
a great way to familiarize yourself with QATrack+ configuration.


Initial Configuration
---------------------

Before you start defining tests and test lists for the first time it is a good
idea to begin by doing some initial configuration.

#. `Change the name of your website <qa/change_site_name.html>`__
#. `Configure the Service Log app <service_log/guide.html>`__ (optional)
#. `Configure the Units app <units/guide.html>`__
#. `Define some Groups and Users <qa/auth.html>`__
#. :ref:`Configure the QA app <initial_qa_config>`


Admin Guide Contents
--------------------

.. toctree::
   :maxdepth: 2

   qa/change_site_name
   units/guide
   qa/guide
   service_log/guide

