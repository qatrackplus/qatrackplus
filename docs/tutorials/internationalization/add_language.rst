.. _add_language:

How to Add a New Language to QATrack+
=====================================

This tutorial will guide you through the process of adding a new language to QATrack+. 
This process involves extracting translatable strings, translating them, compiling them, then configuring 
the system to use the new language.

Prerequisites
------------

- QATrack+ development environment set up
- Python 3.12+ and uv package manager installed
- Translation tools installed (see below)

Supported Languages
------------------

QATrack+ supports any language that Django supports. Common language codes include:

- **French**: ``fr``
- **Spanish**: ``es`` 
- **German**: ``de``
- **Italian**: ``it``
- **Portuguese**: ``pt``
- **Chinese**: ``zh``
- **Japanese**: ``ja``
- **Korean**: ``ko``
- **Russian**: ``ru``

Step 1: Generate Translation Files
----------------------------------

First, you need to extract all translatable strings from your codebase using Django's 
``makemessages`` command:

.. code-block:: bash

    # Generate Django template and Python file translations
    python manage.py makemessages -l es

Replace ``es`` with your desired language code (e.g., ``fr`` for French, ``de`` for German).

This command will:

* Create a new directory structure: ``qatrack/locale/es/LC_MESSAGES/``
* Generate a ``django.po`` file
* Extract all strings marked for translation in your code

Step 2: Translate the Strings
-----------------------------

You now have two options for translating the strings:

**Option A: Manual Translation**
Use `Poedit <https://poedit.net/>`_ to easily edit the .po files.
Alternatively, you can edit the generated ``.po`` file manually using any text editor. Each entry looks like:

.. code-block:: po

    msgid "Welcome to QATrack+"
    msgstr ""

Change the ``msgstr ""`` to your translation:

.. code-block:: po

    msgid "Welcome to QATrack+"
    msgstr "Bienvenido a QATrack+"

**Option B: Automated Translation**
Use the included translation script with Google Translate:

.. code-block:: bash

    # Install translation dependencies (if not already installed)
    uv pip install -e ".[translations]"

    # Translate using the script
    python scripts/translation.py translate es

The script will:

* Automatically translate all strings to your target language
* Preserve format variables like ``%(name)s`` and ``{variable}``
* Skip non-translatable content (numbers, punctuation, etc.)

**Important**: Even with automated translation, manual review and editing will likely still be necessary. 
Always review the results for accuracy, especially:

* Technical terms and medical terminology
* Context-specific language that may not translate well
* Formatting and special characters that may not transfer correctly

Step 3: Compile the Translations
--------------------------------

Once you have translated the strings, compile them into Django's binary format:

.. code-block:: bash

    # Compile all languages
    python manage.py compilemessages

    # Or compile a specific language
    python manage.py compilemessages --locale=es

This creates ``.mo`` files that Django uses at runtime.

Step 4: Configure Language Settings
-----------------------------------

QATrack+ requires explicit configuration of available languages in your local settings. 
The system will only display languages that are explicitly configured in the `LANGUAGES` setting.

In ``qatrack/local_settings.py`` configure the language settings for your environment:

.. code-block:: python

    # Language Configuration
    USE_I18N = True
    USE_L10N = True
    LANGUAGE_CODE = 'es'  # Change to your language code

    # Add locale paths to tell Django where to find translation files
    LOCALE_PATHS = [
        os.path.join(os.path.dirname(__file__), 'locale'),
    ]

**Configure Available Languages (Required)**
You must explicitly define which languages appear in the language selector:

.. code-block:: python

    # Available languages for translation (required)
    LANGUAGES = [
        ('en', 'English'),
        ('es', 'Spanish'),  # Add your new language here
        ('fr', 'French'),
        # Add more languages as needed
    ]

**How it works:**
QATrack+ uses a context processor that scans your locale directory to detect available 
translation files, but only displays languages that are explicitly configured in the 
`LANGUAGES` setting. This gives you full control over which languages are presented 
to users while still maintaining the ability to detect available translations.

Known Issues
-----------

**String Extraction Coverage**

We are aware that not all user-facing strings in QATrack+ are currently being 
caught by Django's ``makemessages`` command. This can happen for various reasons:

- **Dynamic strings**: Some text is generated programmatically and not marked for translation
- **Template variables**: Some strings are passed as variables and not directly in templates
- **JavaScript strings**: Client-side text may not be properly marked for translation
- **Database content**: User-generated content stored in the database
- **Third-party packages**: Some dependencies have strings that aren't marked for translation

**What We're Doing**

We are actively working to improve string extraction coverage by:
- Reviewing and updating model fields and configurations with proper translation decorators
- Adding translation markers to dynamic content generation
- Improving JavaScript internationalization support
- Working with the community to identify and fix missing translations

**Current Status**

While we work on improving coverage, the current translation system will capture 
the majority of static user interface text. You may notice some strings remain 
in English - this is expected and will be addressed in future updates.

**Reporting Missing Strings**

If you notice specific strings that aren't being translated, please:
1. Check if the string appears in the generated ``.po`` file
2. If not, the string may need to be marked for translation in the source code
3. Consider reporting the issue on our GitHub repository so we can improve coverage

Contributing Your Translations
------------------------------

Once you have translated a new language, we encourage you to contribute your work
back to the QATrack+ community. This helps us make the platform more accessible to
users around the world.

You can contribute in several ways:

1.  **GitHub Pull Request**
    If you are comfortable with Git and GitHub, the best way to contribute is by
    creating a pull request. This allows us to review and merge your changes
    efficiently.
    
    **If You Are Not Familiar with Pull Requests, Here's an Overview:**
    
    - **GitHub Pull Request Guide**: `Creating a pull request <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request>`_
    - **Fork and Clone**: `Forking a repository <https://docs.github.com/en/get-started/quickstart/fork-a-repo>`_
    - **Git Basics**: `Git Handbook <https://guides.github.com/introduction/git-handbook/>`_

2.  **GitHub Discussions**
    If you are not familiar with pull requests, you can share your translated
    `.po` file in our GitHub Discussions forum. We can then integrate it
    into the project.

    `QATrack+ GitHub Discussions <https://github.com/qatrackplus/qatrackplus/discussions>`__

3.  **Google Group**
    You can also share your translations or ask for help on our Google Group.

    `QATrack+ Google Group <https://groups.google.com/g/qatrack>`__

We appreciate your contributions to QATrack+!