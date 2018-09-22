Test Packs (Experimental feature)
=================================

.. _testpack_admin:

In order to facilitate the sharing of test lists between different QATrack+
installations (e.g. to allow separate clinics to share test list
configurations) QATrack+ allows users to export/import "Test Packs" which
include complete definitions of Tests, TestLists, and/or TestListCycles.

.. note:: This is currently an experimental feature and will be expanded and improved
        in future versions of QATrack+. A site for publicly sharing test pack
        configurations is planned so that centres around the world can share some or
        all of their test configurations.


Exporting a test pack
---------------------

In order to export a test pack, go to the main admin site and click on `Export
Test Pack` (or visit `/qa/admin/export_testpack/` directly).

On the next screen, you can select all of the TestLists, TestListCycles, and
extra Tests that you want to include in your TestPack.  Note, selecting a
TestList will automatically include all the relevant Tests and SubLists
required for the TestList.


.. image:: images/testpack-export-select.png


After you have selected the items you want to include, enter a name (the name
must consist only of letters, numbers, underscores and hyphens) and brief
description on the right hand side of the page and click `Download`.


.. image:: images/testpack-export-download.png

You can now share this TestPack file with colleagues and they can import
the test configuration to their own system.


Importing a test pack
---------------------


If you have a Test Pack file you want to import, go to the main admin site and
click on `Import Test Pack` (or visit `/qa/admin/import_testpack/` directly).

On the next screen, click the "Choose File..." button on the right hand side of
the page and select your Test Pack file.  Use the tables to select the Test
Lists, Test List Cycles, or individual tests you want to import and then click
the `Import` button on the right.

.. image:: images/testpack-import-select.png


Note if there is a naming conflict between an existing test name (or test
list/test list cycle slug), and a test being imported, QATrack+ will append a
numeral to the name so that existings tests (test lists/test list cylces) will
not be overwritten.

