Developers Guide
================


.. toctree::
   :maxdepth: 3
   :caption: Contents:

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

Python 3.4+
~~~~~~~~~~~

QATrack+ is developed using Python 3 (at least Python 3.4, preferably 3.5+).
Depending on your operating system, Python 3 may already be installed but if
not you can find instructions for installing the proper version on
https://python.org.

Git
~~~

QATrack+ uses the git version control system. While it is possible to download
and modify QATrack+ without git, if you want to contribute code back to the
QATrack+ project, or keep track of your changes, you will need to learn about
git.

You can download and install git from https://git-scm.com. After you have git
installed it is recommended you go through a git tutorial to learn about git
branches, commiting code and pull requests. There are many tutorials available
online e.g. https://www.atlassian.com/git/tutorials, https://try.github.io/.

BitBucket
~~~~~~~~~

The QATrack+ project currently uses `BitBucket <https://bitbucket.org>`__ for
hosting its source code repository.  In general, to contribute code to QATrack+
you will need to create a fork of QATrack+ on BitBucket, make your changes,
then make a pull request to the main QATrack+ project.

Creating a fork of QATrack+
...........................

Creating a fork of QATrack+ is explained in the `BitBucket documentation
<https://confluence.atlassian.com/bitbucket/forking-a-repository-221449527.html>`__.

Cloning your fork to your local system
......................................

Once you have created a fork of QATrack+ on BitBucket, you will want to
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

    pip install -r requirements.dev.txt


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

As of version 0.3.1, all strings and templates in QATrack+ should be marked for
translation. This will allow for QATrack+ to be made avaialable in multiple
languages.  For discussion of how to mark templates and strings for translation
please read the `Django docs on translation
<https://docs.djangoproject.com/en/1.11/topics/i18n/translation/>`__.

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

All new code you write should have tests written for it.  Any non trivial code
you wish to contribute back to QATrack+ will require you to write tests
for the code providing as high a code coverage as possible.  You can measure code coverage
in the following way:

.. code-block:: shell

    make cover



Copyright & Licensing
---------------------

The author of the code (or potentially their employer) retains the copyright of
their work even when contributing code to QATrack+.  However, unless specified
otherwies, by submitting code to the QATrack+ project you agree to have it
distributed using the same `MIT license
<https://bitbucket.org/tohccmedphys/qatrackplus/src/master/LICENSE>`__ as
QATrack+ uses.
