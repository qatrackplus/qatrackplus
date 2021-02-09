.. _win_upgrading_02X_to_031:


Upgrading from versions less than 0.3.0
---------------------------------------

You must first upgrade to v0.3.0 before upgrading to v0.3.1.


Upgrading from version 0.3.0
----------------------------

The steps below will guide you through upgrading a version 0.3.0 installation
to 0.3.1.  If you hit an error along the way, stop and figure out why the error
is occuring before proceeding with the next step!

.. contents::
    :local:


Backing up your database
~~~~~~~~~~~~~~~~~~~~~~~~

It is **extremely** important you back up your database before attempting to
upgrade. It is recommended you use SQLServer Management Studo to dump a backup
file, but you can also generate a json dump of your database (possibly
extremely slow!):

.. code-block:: console


    cd C:\deploy\
    .\venvs\qatrack\bin\Activate.ps1
    cd qatrackplus\
    python manage.py dumpdata --natural > backup-0.3.0-$(date -I).json


Checking out version 0.3.1
~~~~~~~~~~~~~~~~~~~~~~~~~~

First we must check out the code for version 0.3.1:

.. code-block:: console

    git fetch origin
    git checkout v0.3.1


Activate your virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you don't currently have a virtualenv activated, activate it with the
`deactivate` command:

.. code-block:: console

    cd C:\deploy
    .\venvs\qatrack3\Scripts\Activate.ps1

We're now ready to install all the libraries QATrack+ depends on.

.. code-block:: console

    cd C:\deploy\qatrackplus\
    python -m pip install --upgrade pip
    pip install -r requirements\win.txt
    python ..\venvs\qatrack3\Scripts\pywin32_postinstall.py -install
    python manage.py collectstatic


Update your local_settings.py file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now is a good time to review your `local_settings.py` file. There are a few
new settings that you may want to configure.  The settings are documented in
:ref:`the settings page <qatrack-config>`. Most importantly you need to
update your database driver to use `sql_server.pyodbc`. Open your
local_settings.py file and set the DATABASES['default']['ENGINE'] key to
`sql_server.pyodbc`. If you had any `OPTIONS` keys set, you should remove
those:


.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'sql_server.pyodbc',
            'NAME': 'yourdatabasename',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
            'OPTIONS': {
            }
        },
        'readonly': {
            'ENGINE': 'sql_server.pyodbc',
            'NAME': 'yourdatabasename',
            'USER': 'qatrack_reports',
            'PASSWORD': 'qatrackpass',
            'HOST': '',
            'PORT': '',
            'OPTIONS': {
            }
        }
    }


Migrate your database
~~~~~~~~~~~~~~~~~~~~~

The next step is to update the v0.3.0 schema to v0.3.1:

.. code-block:: console

    python manage.py migrate --fake-initial


Restart your CherryPy Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Restart your existing `QATrack CherryPy Service` using the `Services`
Windows application.


Last Word
~~~~~~~~~

There are a lot of steps getting everything set up so don't be discouraged if
everything doesn't go completely smoothly! If you run into trouble, please get
in touch on the :mailinglist:`mailing list <>`.

