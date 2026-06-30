.. _configure_language:

Configuring a Language in QATrack+
==================================

This tutorial will guide you through configuring a language in QATrack+ so that it appears
in the language dropdown menu.

Prerequisites
------------

- QATrack+ development environment set up
- Translation files created and compiled (see :ref:`add_language`)

Overview
--------

After creating translation files for a new language, you need to configure QATrack+ to
recognize and use that language. This includes:

1. Ensuring translation files are properly compiled
2. Configuring local settings to enable the language

Step 1: Verify Translation Files
--------------------------------

First, make sure your translation files are properly compiled. You should have:

- A ``locale/[language_code]/LC_MESSAGES/`` directory
- A compiled ``django.mo`` file in that directory

To compile translations (if you haven't already):

.. code-block:: bash

    # Compile all languages
    python manage.py compilemessages

    # Or compile a specific language
    python manage.py compilemessages --locale=es

Step 2: Configure Local Settings
--------------------------------

Create or edit your ``qatrack/local_settings.py`` file to configure the language settings:

.. code-block:: python

    # Language Configuration
    USE_I18N = True
    USE_L10N = True
    LANGUAGE_CODE = 'en'  # Default language (change as needed)

    # Add locale paths to tell Django where to find translation files
    LOCALE_PATHS = [
        os.path.join(os.path.dirname(__file__), 'locale'),
        os.path.join(os.path.dirname(__file__), '..', 'qatrack', 'locale'),
    ]

    # Available languages for the language selector
    LANGUAGES = [
        ('en', 'English'),
        ('es', 'Spanish'),  # Add your new language here
        ('fr', 'French'),
        ('de', 'German'),
        # Add more languages as needed
    ]

    # Optional: Set default language for new users
    DEFAULT_LANGUAGE = 'en'

Step 3: Language Detection
--------------------------

QATrack+ automatically detects available languages from your locale folders. The system:

- Looks for subdirectories matching language codes (e.g., ``es/``, ``fr/``, ``de/``)
- Automatically makes detected languages available in the interface

Troubleshooting
---------------

**Language doesn't appear in dropdown:**

- Check that ``django.mo`` files exist, is none empty and compiled
- Ensure the language code in your locale folder matches what you're expecting
- Restart the server after configuration changes

**Translations not working:**

- Run ``python manage.py compilemessages`` to ensure .mo files are up to date
- Check that ``USE_I18N = True`` is set
- Verify the language code format (e.g., ``es`` for Spanish, not ``es-ES``)

**Common Language Codes:**

- **Spanish**: ``es``
- **French**: ``fr``
- **German**: ``de``
- **Italian**: ``it``
- **Portuguese**: ``pt``
- **Chinese**: ``zh``
- **Japanese**: ``ja``
- **Korean**: ``ko``
- **Russian**: ``ru``
