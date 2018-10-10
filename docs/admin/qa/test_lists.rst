.. _qa_test_lists:

Configuring Test Lists
======================

To edit existing test lists or create new test lists click on the **Test
Lists** in the **QA** section on the main admin page.

Create a new test list by clicking the **Add Test List** link on the
**Test Lists** admin page. The fields for defining a new test list are
described below.

Name
----

A descriptive name that will be displayed in listings of test-lists.

Slug
----

A `slug is a URL friendly short
label <https://docs.djangoproject.com/en/dev/ref/models/fields/#slugfield>`__
for a test list. It should consist of only letters, numbers, underscores
and hyphens.

Description
-----------

*Optional*

A concise description of what this test list is for.

Warning Message
---------------

Use this field to define the message shown when a test within this test
is at Action level. If the message is left blank The default is ("Do not
treat").

Javascript
----------

You can enter arbitrary Javascript snippets here, and they will be injected
into the page when perfo

.. figure:: images/javascript.png
   :alt: Javascript injection

   Javascript Injection


Test List Members
-----------------

Test List's are composed from :term:`Test` s and/or other Test Lists, called
:term:`Sublist`\s.

In order to add a test to your test list, click the magnifying glass
beside the first text box under the **Test** header.

.. figure:: images/search_for_test.png
   :alt: search for test

   search for test

This will bring up a dialogue box that you can use to search for the
test you want to add (or create a new one).

.. figure:: images/search_results.png
   :alt: Search results

   Search results

Once you've found the test you want to add, clicking on its name will
close the dialogue box and add the test to your test list.

.. figure:: images/test_added_to_list.png
   :alt: Test added to list

   Test added to list

.. _qa_sublists:

Likewise, you can select another Test List to include by using the Sublist entry field:

.. figure:: images/select_sublist.png
   :alt: Adding a Sublist to a Test List

   Adding a Sublist to a Test List

If you need to add more Tests or Sublists, then click the `Add another Test
List Membership` or `Add another Sublist` links.

You can choose to have Sublists distinguished visually by checking the
corresponding `Show Outline Around Sublist` checkbox.

If you now click the **Save and continue editing** button at the bottom
of the page, you will see the name of your test next to its id number.

.. figure:: images/test_added_and_saved.png
   :alt: Test added and saved

   Test added and saved

Continue to add tests in this fashion (you can add many tests without
saving in between) until you have added all the required tests.

When you are finished click \*\*Save and continue editing\* and confirm
that all your tests are present. See the section below for instructions
on how to reorder the tests if required.

Reordering Tests and Sublists within a Test List
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests and Sublist's can easily be reordered by dragging and dropping a tests
row into a new position in the list. After you have finished reordering click
**Save and continue editing** and ensure all your tests are now in the correct
order.

.. figure:: images/drag_and_drop.png
   :alt: Reorder Tests & Sublists

   Reorder Tests & Sublists


Attachments
-----------

You can add arbitrary attachments to a Test List (e.g. a PDF procedure for
performing the Test List) by uploading them using the `Attachments` section at
the bottom of the Test List configuration page.

.. figure:: images/test_list_attachments.png
   :alt: Adding attachments to Test Lists

   Adding attachments to Test Lists
