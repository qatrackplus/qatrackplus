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
~~~~~~~~~~~~~

QATrack+ is developed using Python 3.12. We recommend using the latest stable
version of Python 3.12 for the best development experience and compatibility.

Node.js (Frontend)
~~~~~~~~~~~~~~~~~~

QATrack+ includes a Vue 3 frontend bundle compiled with Vite. Node.js 22 or newer
is required to build it locally. The compiled file is **not** committed to the
repository — release archives include a pre-built copy so deployers have no Node.js
requirement. If you are developing from a ``git clone`` you must build it yourself
(see :ref:`building-frontend` below).

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
.. _building-frontend:

Building the Frontend
~~~~~~~~~~~~~~~~~~~~~

The compiled Vue frontend bundle (``qatrack/qatrack_core/static/dist/faults.js``)
is **not** tracked in version control. Release archives ship with a pre-built copy,
but developers working from a ``git clone`` must generate it manually.

After cloning (and whenever source files under ``qatrack/faults/static/faults/src/``
change), run:

.. code-block:: shell

    npm ci          # install dependencies (once, or after package.json changes)
    npm run build   # compile faults.js into qatrack/qatrack_core/static/dist/

.. note::

    The generated ``faults.js`` file is gitignored — do **not** commit it.

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

    # Activate the virtual environment (Linux/macOS):
    source .venv/bin/activate

On Windows, activate it from PowerShell instead:

.. code-block:: powershell

    .\.venv\Scripts\Activate.ps1

Install development dependencies:

.. code-block:: shell

    # Install all development dependencies
    uv sync --dev

.. note::

    Activating the virtual environment is optional. ``uv sync`` creates and
    manages ``.venv`` for you, and prefixing a command with ``uv run`` (e.g.
    ``uv run pytest``) runs it inside that environment without activation.
    The examples below use the bare ``python``/``pytest`` form, which assumes
    you have activated it; add ``uv run`` in front of each if you would
    rather not. ``AGENTS.md`` and ``CONTRIBUTING.md`` in the repository root
    use the ``uv run`` form throughout.



Creating your development database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rather than using a full blown database server for development work, You can
use Sqlite3 which is included with Python.

Once you have the requirements installed, copy the debug `local_settings.py` and `local_test_settings.py`
files from the deploy subdirectory and then create your database:

.. code-block:: shell

    cp deploy/dev/local_settings.dev.py qatrack/local_settings.py
    cp deploy/dev/local_test_settings.sqlite.py qatrack/local_test_settings.py
    mkdir db
    python manage.py migrate
    python manage.py createcachetable


this will put a database called `default.db` in the `db` subdirectory.
``deploy/dev/`` has a template per engine if you would rather test against
something other than sqlite - see :ref:`local_test_settings_templates` below,
and ``make test-<engine>`` under `Running The Test Suite`_ for running against
one without touching your usual ``local_test_settings.py``.

.. _local_settings_templates:

``local_settings.py`` templates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``deploy/dev/local_settings.dev.py`` above is the right starting point for
development work. The remaining ``local_settings.py`` templates under
``deploy/`` target real deployments rather than development, and are the
ones referred to by the error QATrack+ raises when ``qatrack/local_settings.py``
is missing:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Template
     - Use it for
   * - ``deploy/dev/local_settings.dev.py``
     - Local development (sqlite, ``DEBUG`` on). Start here.
   * - ``deploy/sqlite/local_settings.py``
     - A file-backed sqlite deployment.
   * - ``deploy/postgres/local_settings.py``
     - A PostgreSQL deployment (see also the ``.sql`` role/database setup
       scripts alongside it).
   * - ``deploy/mysql/local_settings.py``
     - A MySQL/MariaDB deployment (likewise with ``.sql`` setup scripts).
   * - ``deploy/win/local_settings.py``
     - A Windows/MS SQL Server deployment.

Copy whichever one matches your target to ``qatrack/local_settings.py`` and
edit it from there. For full deployment instructions see the
:doc:`installation guides </install/install>`, not this page.


.. _local_test_settings_templates:

``local_test_settings.py`` templates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These configure the database the *test suite* runs against, which is separate
from the one the development server uses. There is one per supported engine:

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Template
     - Use it for
   * - ``deploy/dev/local_test_settings.sqlite.py``
     - File-backed sqlite at ``db/default.db``. The default. Needs
       nothing beyond Python.
   * - ``deploy/dev/local_test_settings.memory.py``
     - In-memory sqlite. The fastest option and leaves nothing on disk, so
       it is the one to reach for when iterating. Copy it to
       ``qatrack/local_test_settings.memory.py`` and ``make test-memory``
       works against it.
   * - ``deploy/dev/local_test_settings.postgres.py``
     - PostgreSQL. Needs a reachable server and a ``qatrackplus_test``
       database; edit the placeholder user, password and host first.
   * - ``deploy/dev/local_test_settings.mysql.py``
     - MySQL/MariaDB. Same again, against a ``qatrackplus_test`` database.
   * - ``deploy/dev/local_test_settings.mssql.py``
     - MS SQL Server. Needs the ODBC driver named in the template, and a
       login with ``dbcreator`` rights so the suite can create its own test
       database - which is why the template sets no database name. It also
       shows the ``Trusted_Connection`` form if you would rather use
       Windows-integrated authentication.

Copy one to ``qatrack/local_test_settings.py`` to make it your everyday
choice. To run against an engine *without* disturbing that file, copy it to
``qatrack/local_test_settings.<engine>.py`` instead and use
``make test-<engine>`` - see `Running The Test Suite`_.

The two sqlite variants are not interchangeable for testing purposes: they
exercise different code paths, and CI deliberately runs both.

Understanding the Settings Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ uses a layered approach to Django settings, with each file serving a specific purpose. Understanding this hierarchy will help you configure your development and testing environment.

Every file below is imported with ``from ... import *``, so the *last* one
loaded wins for any given setting. Under a test run the chain is
``settings.py`` -> ``local_settings.py`` -> ``test_settings.py`` ->
``local_test_settings.py``, giving this order:

**Settings File Hierarchy (Highest to Lowest Precedence):**

1. ``local_test_settings.py`` - Your custom test environment overrides

   - Contains all essential development and test settings in one place
   - This is the main file you'll customize for your testing needs

2. ``test_settings.py`` - Default test environment settings

   - Contains test-specific defaults like password hashers and notification
     settings
   - Note that ``test_settings.py`` re-imports ``local_settings.py`` and
     *then* applies its own values, so under a test run it overrides
     anything you set in ``local_settings.py``. If you set, say,
     ``LANGUAGE_CODE`` or ``NOTIFICATIONS_ON`` in ``local_settings.py`` and
     wonder why the tests don't see it, this is why - put test-only values
     in ``local_test_settings.py`` instead.

3. ``local_settings.py`` - Your custom development environment overrides

   - Contains development-specific settings like database configuration
   - This is the file the development server and management commands use;
     outside of a test run it is the highest-precedence file.

4. ``settings.py`` - Base Django application settings

   - Contains core Django configuration, installed apps, middleware, etc.

Collect Static Files
~~~~~~~~~~~~~~~~~~~~

Before running the development server, you need to collect all static files to the STATIC_ROOT directory:

.. code-block:: shell

    python manage.py collectstatic --noinput


Loading Default Data (Fixtures)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ comes with pre-configured default data that provides a foundation for development and testing. This includes common QA categories, test frequencies, modalities, vendors, and other essential data structures.

To load the default data into your development database:

.. code-block:: shell

    python manage.py loaddata fixtures/defaults/*/*.json

This command will populate your database all default data.

You can also load specific fixture categories individually if you only need certain data:

.. code-block:: shell

    # Load only QA-related fixtures
    python manage.py loaddata fixtures/defaults/qa/*.json

    # Load only unit-related fixtures
    python manage.py loaddata fixtures/defaults/units/*.json

    # Load only service log fixtures
    python manage.py loaddata fixtures/defaults/service_log/*.json

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
allow for QATrack+ to be made available in multiple languages. Note that
translatable labels for form fields (i.e. `my_form_field = FieldClass(label=_l("the_label"), ...)`)
and translatable verbose names for model fields (i.e. `my_model_field = ModelClass(verbose_name=_l("the_verbose_name"), ...)`)
are often required for the rendering of translated strings in the frontend, so
the recommendation, as stated in the Django docs, is to always include them.

For discussion
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

QATrack+ uses `ruff <https://docs.astral.sh/ruff/>`__ for linting,
formatting, and import ordering - it replaces the older flake8/yapf/isort
combination entirely, and their config sections have been removed from
``setup.cfg`` (the file itself has been removed - ruff's configuration lives
under ``[tool.ruff]`` in ``pyproject.toml``). Quote style is **single
quotes**, and import ordering is enforced via ruff's ``I`` rule set - no
separate isort pass needed.

``line-length`` is set to **120 characters**, but note that ``E501``
(line-too-long) is in the ``ignore`` list, so ``ruff check`` will *not*
flag an over-long line. 120 is the target ``ruff format`` wraps to, and
until repo-wide formatting has been applied (see below) it is a convention
to aim for rather than something the linter enforces.

To check for violations:

.. code-block:: shell

    uv run ruff check .

Repo-wide ``ruff format`` hasn't been applied to this codebase yet, so avoid
running it across everything - that would surface a large, unrelated
reformatting diff. Scope it to the files you actually changed:

.. code-block:: shell

    uv run ruff format <files you changed>

Before opening a PR, also run the full pre-commit suite (ruff lint plus
``django-upgrade``):

.. code-block:: shell

    uv run pre-commit run --all-files

Using Make Commands
~~~~~~~~~~~~~~~~~~~

QATrack+ includes a Makefile with convenient shortcuts for common development tasks like running tests, formatting code, and building documentation. You can see all available commands by running:

.. code-block:: shell

    make help

For detailed information about using make and understanding Makefiles, refer to the `GNU Make Manual <https://www.gnu.org/software/make/manual/>`_.

Import Order
~~~~~~~~~~~~

Imports should be split into three sections - standard library, third
party, and QATrack+ specific - each in alphabetical order. ``ruff check .``
enforces this automatically (rule set ``I``), so there's no separate tool to
run or configure; ``ruff`` will flag anything out of order and, in most
cases, ``uv run ruff check . --fix`` will reorder it for you.

Indentation
~~~~~~~~~~~

Python code for QATrack+ use 4 spaces for indentation. Django templates (and
other html files) should use 2 spaces for indentation.  Javascript code should
use 4 spaces for indentation.


Setting Up Selenium Browser Testing
-----------------------------------

QATrack+ includes Selenium tests that simulate user interactions with the web interface and are marked with the `@pytest.mark.selenium` decorator.

**Browser Requirements**

You need a browser installed - either Firefox or Chrome/Chromium, whichever
you prefer. You do not normally need to install or configure a matching
driver (geckodriver/chromedriver): Selenium Manager, built into Selenium
4.6+, detects whichever browser you have and fetches a driver to match the
first time a Selenium test runs. No display server is needed either, since
tests run the browser in its own native headless mode by default - so this
behaves the same on a workstation, a CI runner or a sandbox.

There is one case that does need a path set. If a ``geckodriver`` or
``chromedriver`` is already on ``PATH`` and does not match the installed
browser, Selenium Manager prints an incompatibility warning and uses it
anyway. Whether that matters depends on how far apart they are - measured
against Chrome 153, one major version behind still starts a session with
nothing worse than the warning, while three behind fails with
``SessionNotCreatedException``. Rather than work out where your own line is,
treat the warning itself as the signal: either take
the stale driver off ``PATH``, or point
``SELENIUM_FIREFOX_DRIVER_PATH`` / ``SELENIUM_CHROMIUM_DRIVER_PATH`` at one
that matches.

.. code-block:: shell

    # Linux - install whichever browser you don't already have
    sudo apt install firefox
    # - or -
    sudo apt install chromium

On Windows and macOS, install the browser the usual way; Selenium Manager
locates it just the same.

**Configuring Selenium Tests**

Set `SELENIUM_BROWSER` in `qatrack/local_test_settings.py` - or in
`qatrack/local_settings.py`, either is honoured - to pick which browser
drives the tests:

.. code-block:: python

    SELENIUM_BROWSER = 'firefox'   # the default
    # SELENIUM_BROWSER = 'chromium'

That's the only setting most people need. A couple of others (all defined
in `qatrack/settings.py`, overridable the same way) are there if you need
them:

* `SELENIUM_HEADLESS` - `True` by default (native headless mode, no display
  needed). Set to `False`, on a machine with a real display, to watch a
  test execute in a visible browser window - useful when debugging a
  failing Selenium test.
* `SELENIUM_FIREFOX_DRIVER_PATH` / `SELENIUM_CHROMIUM_DRIVER_PATH` - only
  needed if you want to pin a specific driver binary instead of letting
  Selenium Manager resolve one automatically.

Viewport size, and why headless is the reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The suite lays out at **1920x1080 CSS pixels**, and
``TestPerformQC::test_perform_qc_viewport_sizes`` additionally checks the
perform-QC page at three widths - 960x1080 (half of a 1080p display, for
someone working side by side), 1366x768 (a common laptop) and 1920x1080. That
is one ordinary test with three ``subTest`` cases; it is not opt-in and runs in
every Selenium run, including CI's.

Both browsers are launched pinned to a **1:1 device pixel ratio**
(``layout.css.devPixelsPerPx`` for Firefox, ``--force-device-scale-factor``
for Chromium). Without that, a *visible* browser inherits the desktop's
display scaling: on a HiDPI desktop scaled to 187.5% a window that renders
1920x1080 headless reports a CSS viewport of only 1536x997. The pages are laid
out for the wider viewport, so at 1536 CSS pixels controls overlap and clicks
land on whatever is covering them.

**Headless is the reference configuration.** It has no window manager and no
desktop scaling, so the viewport is exactly what was asked for, every time,
on every machine. That is what CI runs and what a layout assertion should be
trusted from.

**Visible mode cannot always control the viewport.** Narrowing to a specific
size needs a viewport override - WebDriver BiDi for Firefox, CDP for
Chromium - and under a Wayland compositor the Firefox one cannot be satisfied,
because the compositor owns the window's geometry. When that happens
``set_viewport_size()`` returns ``False`` rather than hanging, and
``test_perform_qc_viewport_sizes`` **skips the profiles it cannot honour**
rather than measuring whatever size the window happened to be. A skip that
names the profile is the honest result; silently testing one size three times
and reporting three is not.

So: use visible mode to *watch* a test, and headless to *believe* a layout
result.

Both `SELENIUM_BROWSER` and `SELENIUM_HEADLESS` can also be set from the
command line for a single run, instead of edited into a settings file -
useful for a one-off ("just this run, watch it in Chromium instead"):

.. code-block:: shell

    # bash/zsh
    SELENIUM_BROWSER=chromium SELENIUM_HEADLESS=False pytest --run-selenium

    # PowerShell - the inline form above is a parse error here
    $env:SELENIUM_BROWSER='chromium'; $env:SELENIUM_HEADLESS='False'; pytest --run-selenium


Running The Test Suite
----------------------

Once you have QATrack+ and its dependencies installed (and optionally configured
Selenium browser testing above), you can run the test suite from the root
QATrack+ directory using the `pytest` command (configuration lives under
``[tool.pytest.ini_options]`` in ``pyproject.toml``):


.. code-block:: sh

    ./qatrackplus> pytest
    ...
    qatrack/accounts/tests/test_accounts.py ✓✓✓

**Running Different Types of Tests**

.. _running-selenium-tests:

Selenium (GUI/browser) tests are skipped by default - a plain `pytest` run
covers everything else, faster and without needing a browser installed:

.. code-block:: shell

    pytest

Run everything, including Selenium tests:

.. code-block:: shell

    pytest --run-selenium

Run *only* the Selenium tests:

.. code-block:: shell

    pytest -m selenium

`--run-selenium` and `-m selenium` both work - use whichever reads more
naturally for what you're doing.

.. deprecated:: 4.0

    The older `pytest -m "not selenium"`, to exclude the GUI tests
    explicitly, still works - it needs quoting on every shell for no
    benefit now that plain `pytest` does the same thing with nothing to
    type at all. It emits a ``PytestDeprecationWarning`` and will be
    removed in QATrack+ 4.2; switch to plain `pytest`.

To test against a specific database engine without disturbing whatever
``qatrack/local_test_settings.py`` you normally use day to day:

.. code-block:: shell

    make test-sqlite
    make test-memory
    make test-postgres
    make test-mysql
    make test-mssql

Each requires ``qatrack/local_test_settings.<engine>.py`` to already exist -
create it from the matching ``deploy/dev/local_test_settings.<engine>.py``
template first. The target swaps that file in for the run and restores your
previous ``local_test_settings.py`` afterward regardless of whether the
tests passed.

``make test-integration`` goes a step further: provisions a brand-new
sqlite database exactly the way a fresh deployment would (``migrate``,
``createcachetable``, ``collectstatic``, ``createsuperuser``) and runs the
suite with ``--reuse-db`` directly against it, so the whole deployment
sequence is exercised for real rather than just a disposable test database.

For more information on using pytest, refer to the `pytest documentation
<https://pytest.org>`__.

.. important::

    All new code you write should have tests written for it.  Any non trivial code
    you wish to contribute back to QATrack+ will require you to write tests
    for the code providing as high a code coverage as possible.  You can measure code coverage
    in the following way:

    .. code-block:: shell

        make cover


Test order and isolation
~~~~~~~~~~~~~~~~~~~~~~~~

Test order is **deterministic**. pytest collects files in directory order and
runs the tests within each file in definition order, and no order-randomising
plugin is installed - so ``-p no:randomly``, which you may see in other
projects' instructions, does nothing here. Two runs of the same selection
execute in the same order.

That is convenient for reproducing a failure, and it is also how order
dependence survives: a test that only passes because an earlier test left
something behind will keep passing, every time, until someone runs it on its
own.

So when a test fails only as part of a larger run, check that first:

.. code-block:: shell

    # in the suite
    pytest -m selenium

    # on its own - if this passes, the test depends on something before it
    pytest qatrack/service_log/tests/test_selenium.py::TestServiceEventForm::test_create_service_event

``pytest-randomly`` would find this class of bug systematically by shuffling
the order on every run. It has deliberately **not** been adopted yet. Its
value depends on the rest of the suite being predictable, and the Selenium
tests still have residual timing flakiness (see below); adding randomised
ordering on top would mix two sources of nondeterminism and make a red CI run
harder to attribute to either. It would also mean carrying a seed back from CI
to reproduce anything.

If it is adopted, the sensible first scope is the non-Selenium suite - it is
fast, it has no browser timing in it, and order bugs there are worth finding.
Leave the GUI tests on deterministic ordering until they are quiet.

Screenshots when a GUI test fails
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every failing Selenium test leaves a full-page PNG behind in
``selenium-screenshots/``, named after the test that produced it:

.. code-block:: text

    selenium-screenshots/
      qatrack_faults_tests_test_selenium.py__TestFaultForm__test_create_fault.png

The name is the pytest node id with ``/`` and ``::`` substituted, so it maps
straight back to the test without a lookup. The directory is created on demand
and is gitignored; nothing is written when a test passes, and non-GUI tests are
unaffected.

This matters most for a failure you cannot reproduce locally. A traceback says
an element was not found; the picture shows *why* - a button still reading
"Submitting...", a form that never populated, a validation error where none was
expected, a modal sitting over the thing being clicked.

In CI the directory is uploaded as a build artifact, separately per platform and
browser (``selenium-screenshots-linux-chromium``,
``selenium-screenshots-windows-chromium``, and so on). A green run uploads
nothing, so the artifact list itself tells you whether anything failed.

The capture and the decision to keep it are deliberately in two places:

* ``SeleniumTests.tearDown`` takes the screenshot and holds it on the test
  instance.
* the ``pytest_runtest_makereport`` hook in ``conftest.py`` writes it out, and
  only when the test actually failed.

They cannot be merged. For a ``unittest.TestCase``, pytest's report hook does
not run until the whole lifecycle is over - and ``tearDown`` navigates to
``about:blank`` on its way out, so a screenshot taken in the hook would
reliably be a blank page.

If ``tearDown`` never ran - a failure in ``setUp`` or ``setUpClass``, say - the
hook falls back to asking the live driver, which may still be showing something
useful. If that also fails, nothing is saved.

Saving is best-effort by design: the test has already failed, and an error while
writing evidence about it must not replace the real failure in the report, so an
``OSError`` here is swallowed.

Known flakiness in the Selenium suite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A handful of GUI tests fail intermittently under Chromium. They pass under
Firefox, which is the profile of a timing race rather than a real difference
in behaviour between the browsers - a test that asserts on something the
browser has not finished doing yet.

When one of these fails, start with the screenshot (see *Screenshots when a GUI
test fails* above). The picture usually names the problem faster than
re-running locally and hoping.

The pattern to look for is an assertion that runs straight after an action
without waiting for the result of that action. ``click()`` returns as soon as
the click has been *dispatched*; if the click triggers a request, the
assertion after it is racing the response. The fix is to wait for something
observable that means the work finished - usually the success alert:

.. code-block:: python

    self.click("submit-qa")
    self.wait.until(e_c.presence_of_element_located((By.CLASS_NAME, 'alert-success')))
    assert models.TestListInstance.objects.count() == 1

Prefer waiting on a condition to ``time.sleep()``. A sleep is both slower than
it needs to be on a fast machine and too short on a loaded one, which is how
most of these become flaky in the first place.


Areas with no test coverage
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some parts of QATrack+ are not covered by the suite, and cannot currently be
covered without work that has not been done yet. They are listed here so
that a gap is not mistaken for "this is tested and passing".

**LDAP / Active Directory authentication.** QATrack+ supports authenticating
against LDAP and Active Directory through the ``AD_LDAP_*`` settings in
``qatrack/settings.py`` (see :doc:`/install/authentication_backends` for how
to configure it), and this is how a large share of clinical deployments log
their users in. There is **no test coverage for any of it**, anywhere in the
suite, and no supported way to exercise it:

* no fixtures or mock directory,
* no containerised directory server for local development,
* nothing in CI - the ``ldap`` extra is not installed in any CI job, so the
  three tests in ``qatrack/accounts/tests/test_accounts.py`` that need the
  ``ldap`` module are skipped rather than run,
* no documented manual test procedure.

In practice this means a change to the authentication backends can only be
verified by hand, against a real directory server that a contributor must
supply themselves. Treat changes in that area with corresponding caution,
and say so explicitly in the pull request.

The likely shape of a fix, if someone takes it on, is a docker-compose
service running a directory server (``osixia/openldap`` or similar) plus a
matching ``local_test_settings`` template, mirroring how the per-engine
database templates under ``deploy/dev/`` already work. That would also let
CI install the ``ldap`` extra and actually run those three skipped tests.

.. important::

    Whatever shape that takes, **LDAP support must remain independent of the
    database backend**. Authentication and database choice are orthogonal:
    any supported directory configuration has to work against sqlite,
    PostgreSQL, MySQL and MS SQL Server alike, and a site must never have to
    pick a particular database in order to authenticate against their
    directory.

    This matters for how the tests get built, not just for the runtime
    behaviour. The per-engine ``local_test_settings`` templates exist to vary
    *one* axis - the database - so LDAP coverage should be a separate,
    composable axis rather than being folded into any one engine's template.
    Bolting the directory settings onto, say, the sqlite template would make
    the coverage look engine-specific when it is not, and would quietly leave
    the other three engines untested for authentication.


Finding views the browser tests never reach
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The section above lists gaps we already know about. This is how to find the
rest, for views specifically.

A plain coverage report cannot answer the useful question on its own. It tells
you a view is covered, but not by *what* - and a view exercised only by a unit
test that calls it directly has never had its template rendered, its JavaScript
run, or its form submitted by a browser. Those are the views most likely to
break in a way the suite will not notice.

Comparing two runs separates the cases. Because the GUI tests are skipped by
default (see :ref:`above <running-selenium-tests>`), a plain ``pytest`` run is
the everything-except-the-browser baseline, and ``-m selenium`` is its
complement:

.. code-block:: shell

    # Everything except the GUI tests
    coverage run --source=qatrack -m pytest
    coverage report --include="*/views.py" -m > cover/no-selenium.txt

    # The GUI tests only
    coverage run --source=qatrack -m pytest -m selenium
    coverage report --include="*/views.py" -m > cover/selenium-only.txt

    diff cover/no-selenium.txt cover/selenium-only.txt

``cover/`` is already in ``.gitignore``, so the two reports will not end up in
a commit. The ``-m`` flag on ``coverage report`` prints the line numbers that
were never executed, which is what makes the two files comparable.

Read the result as three cases:

* **Covered in both** - exercised by unit tests and by the browser. Nothing to
  do.
* **Covered in the first, missed in the second** - unit tests only. These are
  the best candidates for a new Selenium test, because the parts a browser
  would exercise are precisely the parts nothing is checking.
* **Missed in both** - no coverage at all. Worth a unit test first; a Selenium
  test is a slow and awkward way to get basic coverage of a view.

For a colour-coded view of any single file, ``coverage html --include="*/views.py"``
writes a browsable report to ``htmlcov/``.

Note that 100% line coverage of a view means every line ran, not that anything
about the result was asserted. Treat the numbers as a way of finding untested
areas, not as evidence that the tested ones are correct.


Running the Selenium tests in parallel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``pytest-xdist`` is a development dependency, and the GUI suite can be run
across several worker processes:

.. code-block:: shell

    uv run pytest -m selenium --run-selenium -n 4 --dist loadscope
    uv run pytest -m selenium --run-selenium -n 8 --dist loadscope

Measured on a 16-core machine, full Selenium suite:

.. list-table::
   :header-rows: 1

   * - Run
     - Time
   * - serial
     - ~520s
   * - ``-n 4 --dist loadscope``
     - ~210s

**Use it for the GUI tests only.** The rest of the suite is *slower* under
xdist, not faster - those tests average about 48ms each, so worker startup
costs more than parallelism saves: 57s serial against 60-65s under ``-n``, and
still 60s with a warm ``--reuse-db``, so it is not database setup either. For
that reason ``-n`` is deliberately not in ``addopts``; it is scoped to the one
Makefile target.

What makes it safe here, and why the architecture allows it:

* **Database** - each xdist worker is a separate process, and pytest-django
  gives each its own test database. The in-memory SQLite used in CI is
  naturally per-process.
* **Live server port** - ``LiveServerTestCase`` already binds a free port per
  instance.
* **The single-threaded server** - ``LiveServerSingleThread`` constrains
  concurrency *within* one server, not across processes, so it is not a
  blocker.
* **Display contention** - this is the one headless genuinely solves.
  Visible browsers compete for focus and window placement, which makes them
  effectively unparallelisable; headless browsers have neither.

The real blocker is shared filesystem state: media and upload directories,
and any file-backed database path, would collide between workers and need
per-worker temporary directories.

``--dist loadscope`` is the distribution mode to use, so all tests in a class
stay on one worker and match the existing per-class browser lifecycle.

Why ``pytest-xdist`` specifically, rather than the alternatives:

* **It has to be process-based, not thread-based.** Each parallel unit needs
  its own database connection, its own live-server port and its own browser
  instance. Thread-based runners (``pytest-parallel`` and similar) share a
  process, so they share module-level state - including the
  ``StaticLiveServerTestCase`` machinery and the WebDriver session - which is
  exactly the state that must not be shared here. xdist forks separate
  processes, so the isolation is free rather than something to engineer.
* **pytest-django supports it directly.** It creates a separate test database
  per worker automatically, which is most of the problem solved. Nothing else
  integrates with the database fixture this project already relies on.
* **Django's own ``--parallel`` is not available to us.** It belongs to
  Django's test runner, and this suite runs under pytest - that is the whole
  reason ``manage.py test`` is discouraged elsewhere in this guide. Adopting ``--parallel`` would mean giving up pytest.
* **``--dist loadscope`` matches the architecture.** Browsers are created and
  torn down per test class, so keeping a class together on one worker reuses
  that browser instead of paying startup repeatedly. Runners that split at
  the file or test level would either fragment the class or offer no control.
* **It is maintained by the pytest project itself**, so it tracks pytest
  releases rather than lagging them - which matters for a suite that is
  already pinned to a specific pytest major version.

**Sequencing matters.** The remaining ``time.sleep()`` calls should be
replaced with proper waits *before* any of this is attempted. Parallelism
multiplies flakiness rather than curing it, and the Chromium timing flakes
documented in ``setUpClass`` would become considerably harder to diagnose
spread across several workers.


Customizing Organization Logos
------------------------------

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
browser (at http://127.0.0.1:8008 by default) by running one of the following
commands:

.. code-block:: shell

    make docs-autobuild
    # -or-, to use a different port (e.g. because 8008 is already taken):
    make docs-autobuild port=8010
    # -or-, without the Makefile at all:
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
otherwise, by submitting code to the QATrack+ project you agree to have it
distributed using the same `Apache License, Version 2.0
<https://github.com/qatrackplus/qatrackplus/blob/develop/LICENSE>`__ as
QATrack+ uses (as of version 4.0 - earlier releases were MIT-licensed).


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
