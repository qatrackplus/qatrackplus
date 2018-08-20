Configuring Tests
=================

To access existing tests or to configure a new test, click on the
**Tests** link in the **QA** section on the the main admin page.

Create a new test by clicking the **Add Test** link in the top right
hand page of the **Tests** admin page.  The individual fields for
configuring a tests are described below.

### Name ###

A name that describes what the test is (e.g. something like *Temperature (deg C)* or *0 deg Gantry - Field Size 10.0x10.0cm - X1 (cm)*).

### Macro Name ###

_**Macro name tl;dr**: give your test a short variable name like *ion\_chamber\_reading* or *temperature*.

Every test must be given a macro name which will be used to refer to
this test in composite tests.  The macro name must be a
[valid Python variable name](http://en.wikibooks.org/wiki/Think_Python/Variables,_expressions_and_statements#Variable_names_and_keywords)
(that is it must consist of only letters a-z, letters A-Z, numbers and
underscores) and must not be one of the following reserved words:

    and       del       from      not       while
    as        elif      global    or        with
    assert    else      if        pass      yield
    break     except    import    print
    class     exec      in        raise
    continue  finally   is        return
    def       for       lambda    try


Python programmers generally use lower case only variable names with
words separated by underscores (\_).  That is to say a macro name like
*ion\_chamber\_reading* is preferable to *ionChamberReading*,
*IonChamberReading*, or *Ion\_Chamber\_Reading*.  Note that this is by
convention only and you are free to choose whichever names you like.

It is also highly advised that you use use a descriptive name like
*ion\_chamber\_reading* instead of something like *icr*.  That way
when other people are reading your code it is obvious what your
variable represents.

### Description ###

The description field is the text that is shown when a user clicks on
the test name while performing QA.  This description can be made up of
plain text or html.  An example showing an html description is shown
below along with the way it looks when displayed on the test list
page.

![Test Description in HTML](images/test_description_html.png)

### Procedure ###

The procedure allows you to insert a URL to a more detailed procedure
available elsewhere.  A link to that URL will be shown when the user
clicks on the test name while performing QA as shown below.

![Detailed Procedure Link](images/procedure_link.png)

### Category ###

Choose the [Test Category](categories.md) that this test belongs to.

### Type ###

QATrack+ currently supports 5 different test types as outlined below.

1. **Simple Numerical** A test with a single numerical result
(e.g. *Temperature*)

1. **Boolean** A test with a Yes or No answer (e.g. *Door Interlock
Functional*)

1. **Constant** A non-user editablenumerical constant to be used in
composite tests (e.g. an N\_DW calibration factor).  When you choose
*Constant* for the *Type* field a *Constant Value* text box will
appear for you to enter your numerical constant in.

1. **Multiple Choice** A test where the user selects from a predefined
list of choices.  When you choose *Multiple Choice* for the *Type*
field, a *Choices* text box will appear where you must enter a comma
separated list of choices for the test.  ![](images/mult_choice.png)

1. **Composite** A value calculated based on other test values (e.g. a
temperature pressure correction, or a calculated dose).  Composite
tests are easy to define but allow users to do define complex
calculations with the Python programming language.  Please see the
[Calculated Test Page](calculated.md) for more information on defining
this type of test.

1. **String** Allows the user to enter a short piece of text (e.g. a
user ID)

1.  **String Composite** A *Composite* test that stores a string (text)
rather than a numerical value. Please see the
[Calculated Test Page](calculated.md) for more information on defining
this type of test.

1. **Upload** A test that allows you to upload an arbitrary file and
process it with a Python snippet.  Please see the
[Calculated Test Page](calculated.md) for more information on defining
this type of test.


An example of configuring tests and grouping them into a test list is
given on our [tutorials page](tutorials/tutorials.md).

### Choices (multiple choice test type only) ###

Field to enter a comma separated list of your test choices.

### Constant Value (constant test type only) ###

Field to enter the value your constant test.

### Hidden (composite & constant test types only) ###

Check this option if you want to hide a composite or constant test from display
when performing a test list.


### Display image (upload test types only) ###

Check this option if you want an image uploaded to QATrack+ to be displayed
on the test list page (supported images depend on browser version but generally
jpg, png & gif work well).

### Test Item Visible In Charts ###

Uncheck this option to hide the test from the charting page.  This can
help keep your charting page clean and limited to the tests you
really care about.

### Allow auto review of this test? ###

Indicate whether this test should be auto-reviewable.  For more information
about this option see the [Auto Review page](auto_review.md)

### Skip Without Comment ###

Check this option if you want users to be able to skip this test without being
forced to add a comment (regardless of their commenting permissions).
