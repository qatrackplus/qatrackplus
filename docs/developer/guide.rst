Developers Guide
================


.. toctree::
   :maxdepth: 3
   :caption: Developers Guide Contents:

   self
   schema


Installing QATrack+ For Development
-----------------------------------

Due to the huge volume of tutorials already written on developing software
using Python, Django, and git, only a brief high level overview of getting
started developing for the QATrack+ project will be given here.  That said,
there are lots of steps involved which can be intimidating to newcomers
(especially git!).  Try not to get discouraged and if you get stuck on anything
or have questions about using git or contributing code then please post to the
:mailinglist:`mailing list <>` so we can help you out!

In order to develop for QATrack+ you first need to make sure you have a few
requirements installed.

Python 3.6+
~~~~~~~~~~~

QATrack+ is developed using Python 3 (Python 3.6-3.9).  Depending on your
operating system, Python 3 may already be installed but if not you can find
instructions for installing the proper version on https://python.org.

Git
~~~

QATrack+ uses the git version control system. While it is possible to download
and modify QATrack+ without git, if you want to contribute code back to the
QATrack+ project, or keep track of your changes, you will need to learn about
git.

You can download and install git from https://git-scm.com. After you have git
installed it is recommended you go through a git tutorial to learn about git
branches, commiting code and pull requests. There are many tutorials available
online including a `tutorial by the Django team
<https://dont-be-afraid-to-commit.readthedocs.io/en/latest/>`__ as well as
a tutorial on and `GitHub <https://try.github.io/>`__.


GitHub
~~~~~~

The QATrack+ project currently uses `GitHub <https://github.com>`__ for
hosting its source code repository.  In general, to contribute code to QATrack+
you will need to create a fork of QATrack+ on GitHub, make your changes,
then make a pull request to the main QATrack+ project.

Creating a fork of QATrack+
...........................

Creating a fork of QATrack+ is explained in the `GitHub documentation
<https://guides.github.com/activities/forking/>`__.

Cloning your fork to your local system
......................................

Once you have created a fork of QATrack+ on GitHub, you will want to
download your fork to your local system to work on. This can either be done
using the command line or one of the graphical git apps that are available.
This page assumes you are using bash on linux or the Git Bash shell on Windows.


Setting up your development environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to keep your QATrack+ development environment separate from your
system Python installation, you will want to set up a virtual environment to
install QATrack+'s Python dependencies in it. Using the command line change to
the directory where you installed QATrack+, create a new virtual environment,
and activate the virtual environment:

.. code-block:: shell

    cd /path/to/qatrackplus
    python3 -m venv env
    source env/bin/activate

Then install the development libraries:

.. code-block:: shell

    pip install -r requirements/dev.txt


Creating your development database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rather than using a full blown database server for development work, You can
use Sqlite3 which is included with Python.

Once you have the requirements installed, copy the debug `local_settings.py`
file from the deploy subdirectory and then create your database:

.. code-block:: shell

    cp deploy/local_settings.dev.py qatrack/local_settings.py
    mkdir db
    python manage.py migrate


this will put a database called `default.db` in the `db` subdirectory.

Running the development server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After the database is created, create a super user so you can log into QATrack+:

.. code-block:: shell

    python manage.py createsuperuser

and then run the development server:

.. code-block:: shell

    python manage.py runserver

Once the development server is running you should be able to visit
http://127.0.0.1/ in your browser and log into QATrack+.

Next Steps
~~~~~~~~~~

Now that you have the development server running, you are ready to begin
modifying the code!  If you have never used Django before it is highly
recommended that you go through the official `Django tutorial
<https://docs.djangoproject.com/en/1.11/intro/tutorial01/>`__ which is an
excellent introduction to writing Django applications.

Once you are happy with your modifications, commit them to your source code
repository, push your changes back to your online repository and make a pull
request! If those terms mean nothing to you...read a git tutorial!


QATrack+ Development Guidelines
-------------------------------

The following lists some guidelines to keep in mind when developing for
QATrack+.


Internationalization & Translation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Please mark all strings and templates in QATrack+ for translation. This will
allow for QATrack+ to be made avaialable in multiple languages.  For discussion
of how to mark templates and strings for translation please read the `Django
docs on translation
<https://docs.djangoproject.com/en/2.2/topics/i18n/translation/>`__.

Adding a translation to QATrack+
................................

**Add subdirectories with language code**

Subdirectories named with the language code need to be added to `locale` in the
project root, and each `qatrack/<app>/locale` folder, where `<app>` are the
translatable apps used in QATrack+: `accounts`, `attachments`, `faults`,
`notifications`, `qa`, `qatrack_core`, `reports`, `service_log` and `units`.
Additionally, a similar subdirectory in `qatrack/templates/locale/<language code>`
needs to be created.

.. code-block:: python

   # project root/
   #    locale
   #        <language code>
   #    qatrack
   #    accounts
   #        locale
   #            <language code>
   #    attachments
   #        locale
   #            <language code>
   #    faults
   #        locale
   #            <language code>
   #    notifications
   #        locale
   #            <language code>
   #    qa
   #        locale
   #            <language code>
   #    qatrack_core
   #        locale
   #            <language code>
   #    reports
   #        locale
   #            <language code>
   #    service_log
   #        locale
   #            <language code>
   #    units
   #        locale
   #            <language code>
   #    templates
   #        locale
   #            <language code>

All choices of loanguage codes can be found `here
<http://www.i18nguy.com/unicode/language-identifiers.html>`__ . You can use a
language code with a country code, for example `fr-ca`, or just the base
language code, i.e. `fr`.

**Create message files**

Once the `locale` subdirectories are created, it is
necessary to create the message files in `*.po` format. To do so, go to the
root directory of the project (the one with `manage.py`) and run
`make messages`.

Django will scan the project `html`, `py` and `js` files for
translatable strings and generate any missing `*.po` files. The files are
created under the `locale/<language code>/LC_MESSAGES` folder.

**Translate the strings**

Use a third-party program to edit the `*.po`
message files. These files are in the format of the popular GNU gettext
toolset. Many programs compatible with gettext exist to translate `*.po`
files, e.g. `poedit
<https://poedit.net/>`_ or `weblate
<https://weblate.org/>`_.

**Commit the message files to repo**

The `*.po` files should be commited to the repository.

**Specify datetime formats for the language**

The datetime formats also need
to be localized. To do so, create a module under formats named after the
language code (see 
`Django docs on format localization
<https://docs.djangoproject.com/en/4.0/topics/i18n/formatting/#creating-custom-format-files>`_)
with the following structure and the following contents:

.. code-block:: python

   # formats/
   #    __init__py
   #    <language code>
   #        __init__.py
   #        formats.py

.. code-block:: python

    # formats/__init__.py
    from . import en, fr  # and any other language code

.. code-block:: python

    # formats/<language code>/__init__.py
    from . import formats  # and any other language code

Example `formats/<language code>/formats.py`:

.. code-block:: python

    DATETIME_FORMAT = "Y-M-j H:i"
    DATE_FORMAT = "Y-M-j"
    TIME_FORMAT = "H:i"
    DATE_INPUT_FORMATS = [
        "%Y-%m-%d", 
        "%Y %m %d"
    ]
    DATETIME_INPUT_FORMATS = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y %m %d %H:%M",
        "%Y %m %d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ]
    TIME_INPUT_FORMATS = ["%H:%M", "%H:%M:%S", "%H:%M:%S.%f"]

    # JavaScript formats
    # https://momentjs.com/docs/#/displaying/format/
    MOMENT_DATE_DATA_FMT = "YYYY-MM-DD"
    MOMENT_DATE_FMT = "YYYY-MM-DD"
    MOMENT_DATETIME_FMT = 'YYYY-MM-DD HH:mm'
    # https://flatpickr.js.org/formatting/
    FLATPICKR_DATE_FMT = 'Y-m-d'
    FLATPICKR_DATETIME_FMT = 'Y-m-d H:i'
    # https://api.jqueryui.com/datepicker/
    DATERANGEPICKER_DATE_FMT = 'YYYY-MM-DD'

    # For using in local_settings.py, to translate DATETIME_HELP.
    # Ensure this gives same result as MOMENT_DATETIME_FMT
    # https://docs.python.org/3.9/library/datetime.html#strftime-and-strptime-format-codes
    PYTHON_DATETIME_FORMAT = "%Y-%m-%d %H:%M"


Tool Tips And User Hints
~~~~~~~~~~~~~~~~~~~~~~~~

Where possible all links, buttons and other "actionable" items should have a
tooltip (via a `title` attribute or using one of the bootstrap tool tip
libraries) which provides a concise description of what clicking the item will
do. For example:

.. code-block:: html

    <a class="..."
        title="Click this link to perform XYZ"
        href="..."
    >
        Foo
    </a>

Other areas where tooltips are very useful is e.g. badges and labels where
wording is abbreviated for display. For example:

.. code-block:: html

    <i class="fa fa-badge" title="There are 7 widgets for review">7<i>

    <span title="This X has Y and Z for T">Foo baz qux</span>



Formatting & Style Guide
------------------------

General formatting
~~~~~~~~~~~~~~~~~~

In general, any code you write should be `PEP 8 compatible
<https://www.python.org/dev/peps/pep-0008/>`__ with a few exceptions.  It is
*highly* recommended that you use flake8 to check your code for pep8
violations. A QATrack+ flake8 config file is included with QATrack+, to view
any flake8 violations run:

.. code-block:: python

    make flake8
    # or
    flake8 .

You may also want to use `yapf <https://github.com/google/yapf>`__ which can
automatically format your code to conform with QATrack+'s style guide.  A yapf
configuration sections is included in the setup.cfg file. To run yapf:


.. code-block:: python

    make yapf


Import Order
~~~~~~~~~~~~

Imports in your Python code should be split in three sections:

1. Standard library imports
2. Third party imports
3. QATrack+ specific imports

and each section should be in alphabetical order.  For example:

.. code-block:: python

    import math
    import re
    import sys

    from django.apps import apps
    from django.conf import settings
    from django.contrib.auth.models import Group, User
    from django.contrib.contenttypes.fields import (
        GenericForeignKey,
        GenericRelation,
    )
    from django_comments.models import Comment
    import matplotlib
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import numpy
    import scipy

    from qatrack.qa import utils
    from qatrack.units.models import Unit

`isort <https://isort.readthedocs.io/en/latest/>`__ is a simple tool for
automatically ordering your imports and an `isort` configuration is included in
the setup.cfg file.

Indentation
~~~~~~~~~~~

Python code for QATrack+ use 4 spaces for indentation. Django templates (and
other html files) should use 2 spaces for indentation.  Javascript code should
use 4 spaces for indentation.


Running The Test Suite
----------------------

Once you have QATrack+ and its dependencies installed you can run the test
suite from the root QATrack+ directory using the `py.test` command:


.. code-block:: sh

    ./qatrackplus> py.test
    Test session starts (platform: linux, Python 3.6.5, pytest 3.5.0, pytest-sugar 0.9.1)
    Django settings: qatrack.settings (from ini file)
    rootdir: /home/randlet/projects/qatrack/qatrackplus, inifile: pytest.ini
    plugins: sugar-0.9.1, django-3.1.2, cov-2.5.1

    qatrack/accounts/tests.py ✓✓✓

For more information on using py.test, refer to the `py.test documentation
<https://pytest.org>`__.

.. important::

    All new code you write should have tests written for it.  Any non trivial code
    you wish to contribute back to QATrack+ will require you to write tests
    for the code providing as high a code coverage as possible.  You can measure code coverage
    in the following way:

    .. code-block:: shell

        make cover


Writing Documentation
~~~~~~~~~~~~~~~~~~~~~

As well as writing tests for your new code, it will be extremely helpful for
you to include documenation for the features you have built.  The documentation
for QATrack+ is located in the `docs/` folder and is seperated into the
following sections:

#. **User guide:** Documentation for normal users of the QATrack+ installation.

#. **Admin guide:** Documentation for users of QATrack+ who are responsible for
   configuring and maintaining Test Lists, Units etc.

#. **Tutorials:**  Complete examples of how to make use of QATrack+ features.

#. **Install:** Documentation for the people responsible for installing,
   upgrading, and otherwise maintaining the QATrack+ server.

#. **Developers guide:** You are reading it :)

Please browse through the docs and decide where is the most appropriate place
to document your new feature.

While writing documentation, you can view the documentation locally in your web
browser (at http://127.0.0.1:8008) by running one of the following commands:

.. code-block:: shell

    make docs-autobuild
    # -or-
    sphinx-autobuild docs docs/_build/html -p 8008


Copyright & Licensing
---------------------

The author of the code (or potentially their employer) retains the copyright of
their work even when contributing code to QATrack+.  However, unless specified
otherwies, by submitting code to the QATrack+ project you agree to have it
distributed using the same `MIT license
<https://github.com/qatrackplus/qatrackplus/blob/master/LICENSE>`__ as
QATrack+ uses.


I'm not a developer, how can I help out?
----------------------------------------

Not everyone has development experience or the desire to contribute code to
QATrack+ but still wants to help the project out.  Here are a couple of ways
that you can contribute to the QATrack+ project without doing any software
development:

* **Translations:** Starting in QATrack+ v3.1.0 (sorry this didn't happen yet),
  QATrack+ will have the infrastructure in place to support languages other
  than English.  We will be making translation files available so that the
  community can create translation files for their native languages. Please get
  in touch with randy@multileaf.ca if you are able to help out with this task!

* **Tutorials:** :ref:`Tutorials <tutorials>` are a great way for newcomers to
  learn their way around QATrack+.  If you have an idea for a tutorial, we
  would love to include it in our tutorials section!

* **Mailing List:** QATrack+ has a :mailinglist:`mailing list <>` which
  QATrack+ users and administrators may find useful for getting support and
  discussing bugs and/or features. Join the list and chime in!

* **Spread the word:** The QATrack+ community has grown primarily through word
  of mouth. Please let others know about QATrack+ when discussing QA/QC
  software :)

* **Other:** Have any ideas for acquiring development funding for the QATrack+
  project?  We'd love to hear them!
