Developers Guide
================

.. note::

    **Disclaimer**: This guide was developed and tested on Ubuntu Linux. 
    While the instructions should work on other operating systems, some commands, package names, 
    or installation steps may differ. If you encounter issues on a different OS, please refer 
    to the specific documentation for your platform or reach out to the community for assistance.

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

Prerequisites
~~~~~~~~~~~~

QATrack+ is developed using Python 3.12. We recommend using the latest stable
version of Python 3.12 for the best development experience and compatibility.

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
a tutorial on `GitHub <https://try.github.io/>`__.

.. _forking-repo:
GitHub Account
~~~~~~~~~~~~~~

The QATrack+ project currently uses `GitHub <https://github.com>`__ for
hosting its source code repository. To contribute code to QATrack+
you will need to create a fork of QATrack+ on GitHub, make your changes,
then make a pull request to the main QATrack+ project.

Creating a fork of QATrack+ is explained in the `GitHub documentation
<https://guides.github.com/activities/forking/>`__.

uv Package Manager
~~~~~~~~~~~~~~~~~~~

The QATrack+ project uses `uv <https://docs.astral.sh/uv/>`__, a fast Python
package manager. uv handles Python version management, virtual environments,
and dependency management.

Install uv using the official installer (recommended):

.. code-block:: shell

    # On Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

.. code-block:: shell

    # Alternative method using pip
    pip install uv

For other installation methods or troubleshooting, see the full installation guide at https://docs.astral.sh/uv/getting-started/installation/

Setting up your development environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First create a :ref:`fork <forking-repo>` of the QATrack+ repository on GitHub.

Then clone your fork to your local machine:

.. code-block:: shell

    git clone https://github.com/YOUR_USERNAME/qatrackplus.git

Selecting an Editor or IDE
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use a variety of tools to edit and work on the QATrack+ codebase. Some popular options include:

- **VS Code**: A free, open-source editor with Python and Django support.
- **Cursor**: An AI-powered code editor that integrates with GitHub Copilot and other AI tools.
- **PyCharm**: A Python IDE with advanced Django support.
- **Vim/Neovim**: Lightweight, keyboard-driven editors.
- **Emacs**: Highly customizable editor.

Choose the editor or IDE that best fits your workflow. All you need is a text editor and a terminal to get started!

Creating a Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once you have decided on a text editor or IDE, create a virtual environment with Python 3.12 using uv:

.. code-block:: shell

    # Create virtual environment with Python 3.12
    uv venv --python 3.12

    # Activate the virtual environment:
    source .venv/bin/activate

Install development dependencies:

.. code-block:: shell

    # Install all development dependencies
    uv sync --dev



Creating your development database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rather than using a full blown database server for development work, You can
use Sqlite3 which is included with Python.

Once you have the requirements installed, copy the debug `local_settings.py` and `local_test_settings.py`
files from the deploy subdirectory and then create your database:

.. code-block:: shell

    cp deploy/dev/local_settings.dev.py qatrack/local_settings.py
    cp deploy/dev/local_test_settings.dev.py qatrack/local_test_settings.py
    mkdir db
    python manage.py migrate
    python manage.py createcachetable


this will put a database called `default.db` in the `db` subdirectory.


Understanding the Settings Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ uses a layered approach to Django settings, with each file serving a specific purpose. Understanding this hierarchy will help you configure your development and testing environment.

**Settings File Hierarchy (Highest to Lowest Precedence):**

1. **`local_test_settings.py`** - Your custom test environment overrides
   - Contains all essential development and test settings in one place
   - This is the main file you'll customize for your testing needs

2. **`local_settings.py`** - Your custom development environment overrides
   - Contains development-specific settings like database configuration

3. **`test_settings.py`** - Default test environment settings
   - Contains test-specific defaults like password hashers and notification settings

4. **`settings.py`** - Base Django application settings
   - Contains core Django configuration, installed apps, middleware, etc.

Collect Static Files
~~~~~~~~~~~~~~~~~~~

Before running the development server, you need to collect all static files to the STATIC_ROOT directory:

.. code-block:: shell

    python manage.py collectstatic --noinput


Loading Default Data (Fixtures)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ comes with pre-configured default data that provides a foundation for development and testing. This includes common QA categories, test frequencies, modalities, vendors, and other essential data structures.

To load the default data into your development database:

.. code-block:: shell

    python manage.py loaddata fixtures/defaults/*/*

This command will populate your database all default data.

You can also load specific fixture categories individually if you only need certain data:

.. code-block:: shell

    # Load only QA-related fixtures
    python manage.py loaddata fixtures/defaults/qa/*
    
    # Load only unit-related fixtures
    python manage.py loaddata fixtures/defaults/units/*
    
    # Load only service log fixtures
    python manage.py loaddata fixtures/defaults/service_log/*

Running the development server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After the database is created, create a super user so you can log into QATrack+:

.. code-block:: shell

    python manage.py createsuperuser

and then run the development server:

.. code-block:: shell

    python manage.py runserver 

Once the development server is running you should be able to visit
http://127.0.0.1:8000/ in your browser and log into QATrack+.

Next Steps
~~~~~~~~~~

Now that you have the development server running, you are ready to begin
modifying the code!  If you have never used Django before it is highly
recommended that you go through the official `Django tutorial
<https://docs.djangoproject.com/en/4.2/intro/tutorial01/>`__ which is an
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
allow for QATrack+ to be made available in multiple languages. For discussion
of how to mark templates and strings for translation please read the `Django
docs on translation
<https://docs.djangoproject.com/en/4.2/topics/i18n/translation/>`__.

**Adding a New Language to QATrack+**

For detailed instructions on adding a new language to QATrack+, including step-by-step
workflows and translation automation, please refer to the :ref:`Add Language Tutorial <add_language>` 
in the tutorials section.


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

Using Make Commands
~~~~~~~~~~~~~~~~~~

QATrack+ includes a Makefile with convenient shortcuts for common development tasks like running tests, formatting code, and building documentation. You can see all available commands by running:

.. code-block:: shell

    make help

For detailed information about using make and understanding Makefiles, refer to the `GNU Make Manual <https://www.gnu.org/software/make/manual/>`_.

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


Setting Up Selenium Browser Testing
----------------------------------

QATrack+ includes Selenium tests that simulate user interactions with the web interface and are marked with the `@pytest.mark.selenium` decorator.

**This setup should be completed before running the test suite if you want to see the Selenium tests in action.**

**Browser Requirements**

You will need to have both a browser and its corresponding driver installed on your system:

* Option 1. **Firefox + geckodriver**
* Option 2. **Chromium + chromedriver**

If you are unsure whether or not you have both a browser and its corresponding driver installed, you can run the following commands to check:

**Finding Browser and Driver Paths:**

.. code-block:: shell

    # Check for Firefox browser
    which firefox
    
    # Check for geckodriver
    which geckodriver
    
    # Check for Chromium browser
    which chromium
    
    # Check for chromedriver
    which chromedriver

**Example Output:**

.. code-block::

    /usr/bin/firefox
    /snap/bin/geckodriver
    /snap/bin/chromium
    /usr/bin/chromedriver

**Installing Missing Components**

If you do not have both firefox and geckodriver or both chromium and chromedriver,
you can install either pair using the following commands:

.. code-block:: shell

    # Option 1: Install Firefox and geckodriver
    sudo apt install firefox geckodriver
    
    # Option 2: Install Chromium and chromedriver
    sudo apt install chromium-browser chromium-chromedriver

**Manual Downloads (Alternative Installation)**

If the package manager installation doesn't work or you need a specific version, you can download the drivers manually:

* **geckodriver**: Download from the `official Mozilla website <https://firefox-source-docs.mozilla.org/testing/geckodriver/>`_
* **chromedriver**: Download from the `official Chrome releases <https://chromedriver.chromium.org/downloads>`_

After downloading, make the driver executable and verify the path.


**Configuring Selenium Tests**

You'll need to configure your browser settings in two files. First, update the Selenium configuration in `qatrack/settings.py`:

.. code-block::

    # Selenium Browser Configuration
    # Options: 'firefox', 'chromium'
    SELENIUM_BROWSER = ''
    
    # Browser Driver Paths
    SELENIUM_FIREFOX_DRIVER_PATH = ''  # Path to geckodriver as shown above
    SELENIUM_CHROMIUM_DRIVER_PATH = ''   # Path to chromedriver as shown above
    
    # Headless Mode
    # Set to True to run browsers in headless mode (no visible browser window)
    # Set to False to see the browser during test execution
    SELENIUM_VIRTUAL_DISPLAY = True

Then also update `SELENIUM_VIRTUAL_DISPLAY` in `qatrack/test_settings.py`:

.. code-block::
    
    # In qatrack/test_settings.py:
    SELENIUM_VIRTUAL_DISPLAY = False  # Set to True to use headless browser for testing (requires xvfb)

**Configuration Examples**

**Firefox with visible browser:**

.. code-block::

    # In qatrack/settings.py:
    SELENIUM_BROWSER = 'firefox'
    SELENIUM_VIRTUAL_DISPLAY = False
    SELENIUM_FIREFOX_DRIVER_PATH = '/snap/bin/geckodriver' 
    
    # In qatrack/test_settings.py:
    SELENIUM_VIRTUAL_DISPLAY = False

**Chromium with visible browser:**

.. code-block::

    # In qatrack/settings.py:
    SELENIUM_BROWSER = 'chromium'
    SELENIUM_VIRTUAL_DISPLAY = False
    SELENIUM_CHROMIUM_DRIVER_PATH = '/usr/bin/chromedriver'
    
    # In qatrack/test_settings.py:
    SELENIUM_VIRTUAL_DISPLAY = False

**Headless mode**

.. code-block::

    # In qatrack/settings.py:
    SELENIUM_BROWSER = ''  # This can either be filled in or left blank
    SELENIUM_VIRTUAL_DISPLAY = True
    
    # In qatrack/test_settings.py:
    SELENIUM_VIRTUAL_DISPLAY = True


Running The Test Suite
----------------------

Once you have QATrack+ and its dependencies installed (and optionally configured
Selenium browser testing above), you can run the test suite from the root
QATrack+ directory using the `py.test` command:


.. code-block:: sh

    ./qatrackplus> py.test
    Test session starts (platform: linux, Python 3.6.5, pytest 3.5.0, pytest-sugar 0.9.1)
    Django settings: qatrack.settings (from ini file)
    rootdir: /home/dev/projects/qatrackplus, inifile: pytest.ini
    plugins: django-4.5.2, cov-3.0.0

    qatrack/accounts/tests.py ✓✓✓

**Running Different Types of Tests**

Run all tests (including Selenium):

.. code-block:: shell

    py.test

Run only Selenium tests:

.. code-block:: shell

    pytest -m selenium

Run only non-Selenium tests (faster):

.. code-block:: shell

    pytest -m "not selenium"

For more information on using py.test, refer to the `py.test documentation
<https://pytest.org>`__.

.. important::

    All new code you write should have tests written for it.  Any non trivial code
    you wish to contribute back to QATrack+ will require you to write tests
    for the code providing as high a code coverage as possible.  You can measure code coverage
    in the following way:

    .. code-block:: shell

        make cover


Customizing Organization Logos
-----------------------------

QATrack+ reports include an option to display your organization's logo.

**Adding Your Organization Logo**

1. **Prepare your logo file:**
   - Use a PNG format for best compatibility
   - Recommended size: 200x60 pixels or similar aspect ratio
   - Keep file size reasonable (under 100KB)

2. **Replace the placeholder logo:**
   - Navigate to ``qatrack/reports/static/reports/img/``
   - Replace the existing ``logo.png`` file with your own logo
   - Keep the same filename (``logo.png``) to avoid template changes

3. **Alternative: Use a different filename:**
   - If you prefer a different filename, edit ``qatrack/reports/templates/reports/_header.html``
   - Update all references from ``logo.png`` to your preferred filename
   - Update the alt text and fallback messages as needed

4. **Collect static files:**
   After making changes, run:
   
   .. code-block:: shell
   
       python manage.py collectstatic --noinput

**Logo Display Options**

- **HTML Reports:** Logo is displayed using Django's static file handling
- **PDF Reports:** Logo uses file:// paths for compatibility with PDF generation
- **Error Handling:** If the logo fails to load, nothing is displayed (no fallback message)
- **Visibility Control:** Users can toggle logo display on/off in report settings

**Customizing Logo Text**

To change the alt text:
- Edit ``qatrack/reports/templates/reports/_header.html``
- Update the translation strings for "Organization Logo"
- Add translations to your locale files if using multiple languages

**Note:** The logo functionality is designed to be easily customizable without requiring code changes to the core application.


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
    sphinx-autobuild docs docs/_build/html --port 8008


Version Naming Convention
~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ uses **Eff Ver (Effort Versioning)** for its version naming convention. 
Eff Ver is a versioning strategy that focuses on the effort required to upgrade 
rather than semantic meaning. This approach prioritizes the practical impact on 
users and developers when considering version changes.

For more information about Eff Ver, see the `Eff Ver documentation 
<https://effver.org>`__.

**Version Number Structure**

The version number follows the format `X.Y.Z` where:

- **X (Major)**: Corresponds to the Django LTS release version
  - Currently at 4.0.0 (Django 4.2 LTS)
  - When upgrading to Django 5.2 LTS, version will become 5.0.0
  - This ensures compatibility and upgrade path alignment with Django

- **Y (Minor)**: Feature releases within the same Django LTS cycle
- **Z (Patch)**: Bug fixes and minor improvements

**Examples:**
- 4.0.0: Initial release on Django 4.2 LTS
- 4.1.0: Major feature release while staying on Django 4.2 LTS
- 4.1.1: Bug fix release
- 5.0.0: Upgrade to Django 5.2 LTS


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


* **Translations:** QATrack+ supports multiple languages through its
  internationalization infrastructure. We welcome community contributions for
  translation files in different languages. Use the translation manager script
  to help automate translations, then refine them manually for accuracy.
  See the "Internationalization & Translation" section above for detailed commands.

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
