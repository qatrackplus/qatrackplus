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

.. note::

    **Draft**: this section hasn't been reviewed yet - if something below
    doesn't work for you, please report it on the :mailinglist:`mailing list <>`.

Shell Autocomplete for uv and poe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tab completion for both tools is optional, but worth setting up if you use
them often.

**Requirements:**

- ``uv`` itself (already required above).
- ``poe`` (`poethepoet <https://poethepoet.natn.io/>`__), only if you also
  want to use ``poe <task>`` as a cross-platform alternative to the
  project's ``Makefile`` targets - see ``poe_tasks/*.toml`` (pulled in via
  ``[tool.poe] include`` in ``pyproject.toml``) for the available tasks.
  It isn't a project dependency; install it once, globally, with
  ``uv tool install poethepoet``.
- A shell ``uv``/``poe`` recognize: bash, zsh, fish, PowerShell, elvish
  (``uv``) or nushell (``poe``, in addition to the previous four).

**Enabling completion:**

Both tools generate their own completion script - there is nothing to
install from PyPI or npm. Add the appropriate line to your shell's profile
(``~/.bashrc``, ``~/.zshrc``, ``~/.config/fish/config.fish``, or
PowerShell's ``$PROFILE``), then restart your shell or ``source`` the
profile:

.. code-block:: powershell

    # PowerShell ($PROFILE)
    uv generate-shell-completion powershell | Out-String | Invoke-Expression
    poe _powershell_completion | Out-String | Invoke-Expression

.. code-block:: shell

    # bash (~/.bashrc)
    eval "$(uv generate-shell-completion bash)"
    eval "$(poe _bash_completion)"

    # zsh (~/.zshrc)
    eval "$(uv generate-shell-completion zsh)"
    eval "$(poe _zsh_completion)"

    # fish (~/.config/fish/config.fish)
    uv generate-shell-completion fish | source
    poe _fish_completion | source

.. note::

    ``uv``'s completion is static - it completes ``uv``'s own subcommands
    and flag names (e.g. ``uv sync --e<TAB>`` -> ``--extra``), but it does
    not read this project's ``pyproject.toml``, so it will not suggest the
    actual extra names (``mysql``, ``mssql``, ``postgres``, ``win``,
    ``docker``, ``translations``) after ``--extra``. There's currently no
    way to get that from ``uv`` itself.

    ``poe``'s completion, in contrast, reads ``pyproject.toml`` each time it
    runs, so ``poe <TAB>`` lists this project's actual task names. It can
    also complete a task argument's allowed values, but only for arguments
    that declare a ``choices`` list in ``pyproject.toml`` - none of this
    project's task arguments do that yet.

.. _adding-a-poe-task:

Adding a new poe task
~~~~~~~~~~~~~~~~~~~~~

Task definitions live under ``poe_tasks/``, one file per theme, rather than
directly in ``pyproject.toml``: ``dev.toml`` (dev environment setup),
``tests.toml`` (running the suite, GUI/Selenium variants), ``coverage.toml``,
``docs.toml`` (Sphinx, schema diagram, translation status), ``data.toml``
(fixtures and destructive data commands) and ``deploy.toml`` (Ubuntu/sudo
deployment helpers). ``pyproject.toml`` itself only lists them, via
``[tool.poe] include``; it never grew a ``[tool.poe.tasks.*]`` table of its
own. This split exists purely to stop ``pyproject.toml`` growing without
bound as tasks are added - it changes nothing about how a task runs, or how
``poe <task>``/``poe --help`` behave.

``poe_tasks/make_compat.toml`` is different in kind, not just location: it
holds the ``make-*`` tasks that deliberately mirror a ``Makefile`` target
one-for-one (see the comment above ``[tool.poe] include`` in
``pyproject.toml``), plus the shared ``_test-engine`` implementation they
``ref``. Nothing new should be added there - a new task belongs in one of
the theme files above, and only gets a ``make-*`` mirror if the ``Makefile``
target it mirrors still exists.

When adding a task:

1. Pick the theme file that matches, or add a new ``poe_tasks/<theme>.toml``
   and list it in ``pyproject.toml``'s ``[tool.poe] include`` if none fit.
2. Included files use bare ``[tasks.<name>]`` headers, **not**
   ``[tool.poe.tasks.<name>]`` - poe treats a non-``pyproject.toml`` file
   with no ``tool.poe`` table of its own as if its entire contents sat under
   ``tool.poe``. Copy the header style already used in that file.
3. Make it work on Windows: prefer a plain ``cmd`` task, or
   ``interpreter = "python"`` with stdlib (``pathlib``/``shutil``/
   ``subprocess``) if it needs any logic at all. Avoid a bare ``shell``
   task (defaults to bash/POSIX, which fails outright on a Windows host
   with no Git Bash or WSL) unless the task is genuinely Ubuntu/sudo-only
   by nature (see ``deploy.toml``) - in that case, say so in the task's
   ``help`` text the way ``nginx-conf`` and ``supervisor-conf`` do.
4. If the task declares a named argument (``options = [...]``), poe will
   silently drop any extra dash-prefixed tokens passed after it rather than
   forwarding them - see the note on ``_test-engine`` in
   ``poe_tasks/make_compat.toml`` for the reasoning. Prefer a positional
   argument, or no argument at all, unless you specifically need the
   ``--flag`` form.
5. A task's argument can declare ``choices = [...]`` to get real tab
   completion of its allowed values (see `Shell Autocomplete for uv and poe`_
   above) - worth adding for anything with a small, fixed set of valid
   values (an engine name, a browser name, and so on).
6. Run ``poe <task>`` for real, not just ``poe -d <task>`` (dry-run only
   prints the resolved command/script - it does not catch a task that
   parses fine but fails or misbehaves once actually invoked).

Setting up your development environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First create a :ref:`fork <forking-repo>` of the QATrack+ repository on GitHub.

Then clone your fork to your local machine:

.. code-block:: shell

    git clone https://github.com/YOUR_USERNAME/qatrackplus.git

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

.. _generating-sample-data:

Generating Sample Data
~~~~~~~~~~~~~~~~~~~~~~

The default fixtures give you an empty, correctly configured QATrack+. To get a
database that actually *looks* like a working clinic — useful when developing a
feature or reviewing someone else's pull request — use the
``generate_sample_data`` command:

.. code-block:: shell

    python manage.py generate_sample_data

This creates a small radiation oncology centre: two linacs and a CT simulator,
TG-142 style daily and monthly test lists with per unit references and
tolerances, 90 days of rolling QA history (including an unreviewed backlog and
one in-progress session to resume), service events with return to service QA,
faults, a parts inventory with a low stock item, and saved reports with email
schedules.

Options:

``--days N``
    How many days of rolling QA history to generate (default 90). Must be zero
    or greater. The service and fault records are placed at fixed offsets and
    are created regardless of this value.

``--clear``
    Delete the existing units, QA, service log, fault, parts and report data
    before generating. You are asked to confirm first.

``--no-input``
    Skip that confirmation, for scripted use.

.. warning::

    ``--clear`` deletes **all** of that data in the database, not just rows a
    previous run created. Only use it on a development database.

The generator creates the following accounts to attribute the data to, all with
the same password. It is defined as ``DEFAULT_SAMPLE_PASSWORD`` in
``qatrack/qatrack_core/sample_data/small.py`` — currently ``password123`` — and is
deliberately well known: these accounts exist so sample records have an author, and
they belong only on a development database.

=====================  =====================================
Username               Groups
=====================  =====================================
``admin``              QA Administrators (superuser)
``jane.physicist``     Medical Physicists, QA Administrators
``mark.physicist``     Medical Physicists
``alex.resident``      Medical Physicists
``sarah.therapist``    Radiation Therapists
``dave.engineer``      Service Engineers
=====================  =====================================

If one of those usernames already exists it is reused rather than replaced: the
account keeps its own password (unless it has no usable one, in which case it
is given the sample password so you can log in) and its existing groups, to
which the groups above are added. ``--clear`` does not delete user accounts.

Running the command again without ``--clear`` extends the sample data rather
than duplicating it — QA sessions, service events and reports that are already
there are left alone. Any default fixtures the generator depends on are loaded
automatically if their tables are empty, so a fresh database needs nothing but
``migrate``.

Collect Static Files
~~~~~~~~~~~~~~~~~~~~

Before running the development server, you need to collect all static files to the STATIC_ROOT directory:

.. code-block:: shell

    python manage.py collectstatic

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

Selecting an Editor or IDE
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use a variety of tools to edit and work on the QATrack+ codebase. Some popular options include:

- **VS Code**: A free, open-source editor with Python and Django support.
- **Cursor**: An AI-powered code editor that integrates with GitHub Copilot and other AI tools.
- **PyCharm**: A Python IDE with advanced Django support.
- **Vim/Neovim**: Lightweight, keyboard-driven editors.
- **Emacs**: Highly customizable editor.

Choose the editor or IDE that best fits your workflow. All you need is a text editor and a terminal to get started!

Node.js (not currently required)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ had a Vue 3 frontend bundle compiled with Vite. The faults UI now uses
server-rendered HTMX with jQuery, and ``package.json`` was removed along with the
bundle, so **Node.js is not a prerequisite for anything today**.

A frontend build is expected to return no earlier than 4.1. Until then there is
nothing to build, and ``npm`` commands will fail for want of a manifest
(see :ref:`building-frontend` below).

.. _building-frontend:

Building the Frontend
~~~~~~~~~~~~~~~~~~~~~

There is nothing to build at present.

The Vue/Vite bundle was retired when the faults UI moved to server-rendered
HTMX, and ``package.json`` went with it, so ``npm ci`` has no manifest to read.
A replacement is expected no earlier than 4.1.

The release workflow builds the frontend only when a ``package.json`` is
present, so it will resume on its own once one is - nothing here needs changing
at that point.

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
~~~~~~~~~~~~~~~~~~~~~~~~

General formatting
^^^^^^^^^^^^^^^^^^

QATrack+ uses `ruff <https://docs.astral.sh/ruff/>`__ for both linting and
formatting, configured in ``pyproject.toml`` under ``[tool.ruff]``. To check your
code:

.. code-block:: shell

    uv run ruff check .

.. warning::

    **Format only the files you changed.** The repository has never been formatted
    as a whole, so ``ruff format .`` rewrites hundreds of files and buries your
    change:

    .. code-block:: shell

        uv run ruff format path/to/the/file/you/changed.py

``uv run pre-commit run --all-files`` before opening a pull request runs what CI
runs.

.. note::

    Earlier versions of this guide described ``flake8``, ``yapf`` and ``isort``, and
    ``make flake8`` / ``make yapf`` targets. None of those tools is installed any
    more and neither target exists; ``setup.cfg`` still carries their configuration
    sections, which are dead and will be removed separately.

Import Order
^^^^^^^^^^^^

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

Import order is checked by ruff's ``I`` rules, which are enabled in
``pyproject.toml``. ``uv run ruff check --fix .`` sorts them, scoped to the files
you changed as above.

Indentation
^^^^^^^^^^^

- **Python**: 4 spaces.
- **Templates and other HTML** - every ``.html`` file under a ``templates/``
  directory, which is where QATrack+'s templates live: 2 spaces.
- **JavaScript** that QATrack+ owns: 4 spaces. Vendored libraries under
  ``static/`` keep whatever their upstream uses; do not reformat them.

**Match the file you are editing before you match this list.** The existing code is
not consistent - of 213 template files, 138 use 2 spaces and 58 use 4; of 88
JavaScript files that are ours rather than vendored, 52 use 4 and 25 use 2. A patch
that reindents a file to follow this page is a patch whose diff hides its own
change.

Using Make Commands
~~~~~~~~~~~~~~~~~~~

QATrack+ includes a Makefile with convenient shortcuts for common development tasks like running tests, formatting code, and building documentation. You can see all available commands by running:

.. code-block:: shell

    make help

For detailed information about using make and understanding Makefiles, refer to the `GNU Make Manual <https://www.gnu.org/software/make/manual/>`_.

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
Chromium. The Firefox one is not guaranteed to succeed, and when it fails it
fails by *hanging*: the BiDi command times out after about 30 seconds, once per
test class. That was observed on a HiDPI desktop where the browser laid out in a
mis-scaled coordinate space; pinning the device pixel ratio fixed it, and the
override now applies on that same machine, Wayland included. The guard is kept
because the failure mode costs a whole suite run, not because any platform is
known to need it. When it does fail, ``set_viewport_size()`` returns ``False``
after that one timeout rather than repeating it per class, and
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

New code should come with tests covering as much of it as you can manage. You can
measure coverage with:

.. code-block:: shell

    make cover

.. tip::

    **Testing is not solely the author's job.** If you are not sure how to test a
    change, or cannot cover all of it, open the pull request anyway and say so - a
    maintainer can help with the tests. A contribution held back because its tests
    were hard is worth less to everyone than one that arrives and gets finished
    together.

Writing Documentation
---------------------

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

The documentation build treats warnings as errors, so a build that reports a
warning fails. Run it the way CI does before you push:

.. code-block:: shell

    rm -rf docs/_build
    uv run sphinx-build -W --keep-going -a --fresh-env -b html docs docs/_build/html

Removing ``docs/_build`` matters. Sphinx caches what it has already parsed, and an
incremental build does not repeat a warning it reported last time - so a warning you
introduced can be invisible to you and fail for the next person.

Fragments, and the leading underscore
-------------------------------------

A page that would otherwise be written out three times - once per platform, say -
can be factored into a fragment and pulled into each page with ``.. include::``.
``docs/install/_upgrade_4_0_before.rst`` is one.

**Name a fragment with a leading underscore, and add it to ``exclude_patterns`` in
``docs/conf.py``.** Both, because they do different jobs:

- **The underscore is for people.** It says this file is not a page and is not meant
  to be read on its own. Sphinx attaches no meaning to it whatsoever - unlike Sass
  partials or Jekyll's ``_includes``, where the convention is enforced by the tool.
  The names ``_build``, ``_static`` and ``_templates`` are special only because
  ``conf.py`` points at them.
- **``exclude_patterns`` is what gives it effect**, and it is worth knowing exactly
  what it prevents. Without it Sphinx reads the fragment as a document *as well as*
  including it. With a fragment that defines no labels - which is what
  ``docs/install/_upgrade_4_0_*.rst`` are today - the build still passes, and the
  only consequence is a published page duplicating content that already appears in
  three guides.

  **The moment a fragment defines a label, that changes.** Measured: adding one
  ``.. _label:`` to an un-excluded fragment produces **three** duplicate-label
  warnings, one for each page that includes it plus the fragment itself, and ``-W``
  turns those into a failed build. So excluding a fragment is cheap insurance that
  becomes necessary the first time somebody writes a label in one, which is not a
  thing anyone will remember to check.

``exclude_patterns`` matches ``**/_*.rst``, so a new fragment named with the
underscore is excluded without further work. Keep the convention anyway: the pattern
is what makes the build pass, and the name is what tells the next person why the file
exists.

Give a fragment a comment at the top saying which pages include it. A reader who
opens it directly has no other way to find out, and ``git grep`` for the filename is
a poor substitute for a sentence.

Version Naming Convention
-------------------------

QATrack+ uses **Eff Ver (Effort Versioning)** for its version naming convention. 
Eff Ver is a versioning strategy that focuses on the effort required to upgrade 
rather than semantic meaning. This approach prioritizes the practical impact on 
users and developers when considering version changes.

For more information about Eff Ver, see the `Eff Ver documentation 
<https://effver.org>`__.

**Version Number Structure**

The version number follows the format `X.Y.Z` where:

- **X (Major)**: Corresponds to the Django LTS release version
  - Currently at 4.0.1 (Django 4.2 LTS)
  - When upgrading to Django 5.2 LTS, version will become 5.0.0
  - This ensures compatibility and upgrade path alignment with Django

- **Y (Minor)**: Feature releases within the same Django LTS cycle
- **Z (Patch)**: Bug fixes and minor improvements

**Examples:**
- 4.0.0: Initial release on Django 4.2 LTS
- 4.0.1: Bug fix release on the same Django LTS
- 4.1.0: Major feature release while staying on Django 4.2 LTS
- 4.1.1: Bug fix release
- 5.0.0: Upgrade to Django 5.2 LTS

Copyright & Licensing
---------------------

The author of the code (or potentially their employer) retains the copyright of
their work even when contributing code to QATrack+.  However, unless specified
otherwise, by submitting code to the QATrack+ project you agree to have it
distributed under the same `Apache License 2.0
<https://github.com/qatrackplus/qatrackplus/blob/master/LICENSE>`__ that
QATrack+ uses.

Releases before 4.0 were MIT-licensed; 4.0 onwards are Apache 2.0, and the
licence holder remains the Ottawa Cancer Centre. See the README for the note on
that change.

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
