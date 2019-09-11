.. _qatrack-config:

Configuring a QATrack+ Installation
===================================

QATrack+ Local Settings
-----------------------

Local settings allow you to override the default QATrack+ settings to better
meet your clinics needs.  The most important settings are explained below.

These settings should be defined in a `local_settings.py` file in the main
directory (same directory as `settings.py`)

.. note::

    Any time you change a setting in local_settings.py, you need to restart the
    QATrack+ application either by restarting Apache or restarting the CherryPy
    Windows Service.


Mandatory Settings
~~~~~~~~~~~~~~~~~~


DEBUG Setting
.............

When deploying your site for clinical use, you should set:

.. code-block:: python

    DEBUG = False

however, when you are experiencing issues getting your site deployed, setting:

.. code-block:: python

    DEBUG = True

will show you a detailed error traceback which can be used to diagnose any
issues.

.. danger::

    It is important to not use DEBUG = True during normal service as it
    may affect site performance and security.


Allowed Host Setting
....................

If you are behind a hospital firewall you can set the `ALLOWED_HOSTS` setting to:

.. code-block:: python

    ALLOWED_HOSTS = ['*']

otherwise you need to set allowed hosts either to your server name or IP
address (e.g. for Apache):

.. code-block:: python

    ALLOWED_HOSTS = ['52.123.4.9']

or if you are running QATrack+ behind a reverse proxy (e.g. using IIS &
CherryPy or nginx):

.. code-block:: python

    ALLOWED_HOSTS = ['127.0.0.1']

HTTP or HTTPS Setting
.....................

In order for urls to use the correct protocol for links, set `HTTP_OR_HTTPS` to
the appropriate protocol.

.. code-block:: python

    HTTP_OR_HTTPS = 'http'  # when using http for your site (default)
    # -or -
    HTTP_OR_HTTPS = 'https'  # when using https/ssl for your site


DATABASES Setting
.................

The database setting is covered in more detail in the `Django documentation
<https://docs.djangoproject.com/en/2.1/ref/settings/#databases>`__ as well as
the QATrack+ deployment documentation.

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'qatrackplus',
            'USER': 'qatrack',
            'PASSWORD': 'qatrackpass',
            'HOST': 'localhost',
            'PORT': '5432',
        },
        'readonly': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'qatrackplus',
            'USER': 'qatrack_reports',
            'PASSWORD': 'qatrackpass',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }


Cache Settings
~~~~~~~~~~~~~~

By default QATrack+ stores cached pages and values on disk in the directory
`qatrack/cache/cache_data/` but this can be changed by copying the Python
dictionary below into your `local_settings.py` file:

.. code-block:: python

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': '/path/to/your/desired/cache/data/location/',
            'TIMEOUT': 24*60*60, # cache timeout of 24hours
        }
    }

Generally you shouldn't need to change this unless you have concerns about disk
usage.

Time Zone Settings
~~~~~~~~~~~~~~~~~~

By default QATrack+ is configured to use North American Eastern Standard Time
so you will need to adjust this to reflect your local time zone.

In your *local_settings.py* file add a line like the following:

.. code-block:: python

    TIME_ZONE = 'America/Toronto'

where 'America/Toronto' is replaced with your local timezone (e.g. `TIME_ZONE =
'Australia/Sydney'`.  If you are unsure, you can find a list of `valid
timezones on Wikipedia
<http://en.wikipedia.org/wiki/List_of_tz_database_time_zones>`_.


Icon Settings
~~~~~~~~~~~~~

By default QATrack+ will show icons to indicate the pass/fail or
due/overdue/not due status of tests and test lists.

Examples of the icons can be seen on `BitBucket
<https://bitbucket.org/tohccmedphys/qatrackplus/pull-request/11/add-icons-to-reduce-dependence-on-red/diff>`_

To override the default settings, copy the following Python dictionary to your
`local_settings.py` file and change the relevant setting to True/False.

.. code-block:: python

    ICON_SETTINGS = {
        'SHOW_STATUS_ICONS_PERFORM':  True,
        'SHOW_STATUS_ICONS_LISTING':  True,
        'SHOW_STATUS_ICONS_REVIEW':  True,
        'SHOW_STATUS_ICONS_HISTORY':  False,
        'SHOW_REVIEW_ICONS':  True,
        'SHOW_DUE_ICONS':  True,
    }



* `SHOW_STATUS_ICONS_PERFORM` controls whether the icons are shown when a user
  is performing a test list.

* `SHOW_STATUS_ICONS_LISTING` controls whether icons are shown on listings
  pages which show the results of the last QC session. (Default True)

* `SHOW STATUS_ICONS_REVIEW` controls whether the icons are shown when a user
  is reviewing a test list. (Default True)

* `SHOW STATUS_ICONS_HISTORY` controls whether the icons are shown for
  historical results when a user is performing or reviewing a test list.
  (Default False)

* `SHOW_REVIEW_ICONS` control whether to show warning icon for unreviewed test
  lists. (Default True)

* `SHOW_DUE_ICONS` control whether to show icons for the due status of test
  lists. (Default True)

Tolerance Naming Settings
~~~~~~~~~~~~~~~~~~~~~~~~~

By changing the following settings you can alter the phrasing that QATrack+
uses for indicating whether a test is passing/failing. The
`TEST_STATUS_DISPLAY_SHORT` settings are used when performing a test list and
the `TEST_STATUS_DISPLAY` settings are used in notifications and when
displaying historical results.

.. code-block:: python

    TEST_STATUS_DISPLAY = {
        'action': "Action",
        'fail': "Fail",
        'not_done': "Not Done",
        'done': "Done",
        'ok': "OK",
        'tolerance': "Tolerance",
        'no_tol': "No Tol Set",
    }

    TEST_STATUS_DISPLAY_SHORT = {
        'action': "ACT",
        'fail': "Fail",
        'not_done': "Not Done",
        'done': "Done",
        'ok': "OK",
        'tolerance': "TOL",
        'no_tol': "NO TOL",
    }

The meaning of the individual keys is as follows:

* `action`: Test is failing or at action level (shown to users with permission
  to view Refs/Tols)

* `fail`: Test is failing or at action level (shown to users without permission
  to view Refs/Tols)

* `not_done`: Test was not completed

* `done`: Test was completed

* `ok`: Test is passing / within tolerance

* `tolerance`: The test is at tolerance (shown to users with permission to view
  Refs/Tols)

* `no_tol`: No tolerances set for this test


Other Settings
~~~~~~~~~~~~~~

AUTO_REVIEW_DEFAULT
...................

Set `AUTO_REVIEW_DEFAULT = True` in your `local_settings.py` file in order to
enable :ref:`Auto Review <qa_auto_review>` by default.

CHROME_PATH
...........

Set `CHROME_PATH` to the Chrome/Chromium executable for generating PDF reports. For example

.. code-block:: python

    CHROME_PATH = '/usr/bin/chromium-browser'  # default
    # - or -
    CHROME_PATH = 'C:/path/to/chromium.exe'  # on Windows



CONSTANT_PRECISION (deprecated. Use DEFAULT_NUMBER_FORMAT instead)
..................................................................

Set the `CONSTANT_PRECISION` setting to adjust the precision for which
:ref:`Constant test type <qa_test_types>` values are displayed. (default 8)

DEFAULT_NUMBER_FORMAT
.....................

Default formatting string to be used for Composite & Constant number formatting
(can be overridden on a test by test basis). Set to a Python style string
format for displaying numerical results.  Use e.g. %.2F to display as fixed
precision with 2 decimal places, or %.3E to show as scientific format with 3
significant figures, or %.4G to use 'general' formatting with up to 4
significant figures. (Note this does not affect the way other values are
calculated, only the way composite and constant test values are *displayed*.
For example a constant test with a value of 1.2345 and a format of %.1f will be
displayed as 1.2, but the full 1.2345 will be used for calculations).  Note you
may also use "new style" Python string formatting: see https://pyformat.info/
for examples.

.. code-block:: python

    DEFAULT_NUMBER_FORMAT = "%.3f"  # 3 decimal place fixed precision using "Old" style formatting
    DEFAULT_NUMBER_FORMAT = "{:.3f}"  # 3 decimal place fixed precision using "New" style formatting
    DEFAULT_NUMBER_FORMAT = "{:.4E}"  # 5 sig fig scientific notation using "New" style formatting


DEFAULT_GROUP_NAMES
...................

A list of group names to automatically add users to when they sign up (default
is an emtpy list):

.. code-block:: python

    DEFAULT_GROUP_NAMES = ["Therapists"]

DEFAULT_WARNING_MESSAGE
.......................

Set `DEFAULT_WARNING_MESSAGE = "Your custom message"` to change the default
warning message that will be shown when a performed test is at action level.
If `DEFAULT_WARNING_MESSAGE = ""` then the default will be to not show any
warning message when a test is at action level.

FORCE_SCRIPT_NAME, LOGIN_EXEMPT_URLS, LOGIN_REDIRECT_URL, LOGIN_URL
...................................................................

If you deploy QATrack+ at a non root url (e.g. http://5.5.5.5/qatrack/) then you need to
set these settings as follows:

.. code-block:: python

    FORCE_SCRIPT_NAME = '/qatrack'
    LOGIN_EXEMPT_URLS = [r"^qatrack/accounts/", r"qatrack/api/*"]
    LOGIN_REDIRECT_URL = 'qatrack//qa/unit/'
    LOGIN_URL = "/qatrack/accounts/login/"


NHIST
.....

Adjusts the number of historical test results to show when reviewing/performing
QC. Default is `NHIST = 5`.

ORDER_UNITS_BY
..............

Set `ORDER_UNITS_BY = 'name'` in your `local_settings.py` file in order to
order units by `name` rather than `number`

REVIEW_DIFF_COL
...............

Set `REVIEW_DIFF_COL = True` to include a difference column when reviewing test
list results. This column shows the difference between a test value and its
reference value.


SL_ALLOW_BLANK_SERVICE_AREA
...........................

Set `SL_ALLOW_BLANK_SERVICE_AREA = True` to allow users to create a ServiceEvent with
a blank ServiceArea set.  When a Service Event is saved without a ServiceArea explicitly set,
the ServiceArea will be set to "Not Specified".


TESTPACK_TIMEOUT
................

Change the number of elapsed seconds before exporting a TestPack will time out.
Default is 30.

USE_SERVICE_LOG
...............

Set `USE_SERVICE_LOG` to `False` in order to disable Service Log

USE_PARTS
.........

Set `USE_PARTS` to `False` in order to disable the Parts app (Service Log
requires `USE_PARTS = True`).

USE_SQL_REPORTS
...............

Set `USE_SQL_REPORTS` to `False` in order to disable the SQL Query tool

USE_X_FORWARDED_HOST
....................

Set `USE_X_FORWARDED_HOST = True` when running QATrack+ behind a reverse proxy
and set to False for whenever you are not running behind a reverse proxy e.g.
Set to True for CherryPy/IIS and False for Apache/mod_wsgi or development work.


SESSION Settings
~~~~~~~~~~~~~~~~

These settings control how quickly users are automatically logged out of an
active browser session.  `SESSION_COOKIE_AGE` specifies how long (in seconds) a
user can use a browser session without having to log in again (default 2
weeks). However, if `SESSION_SAVE_EVERY_REQUEST` is `True` the session age will
be reset every time a user is active and hence allows them to stay logged in
indefinitely.

.. code-block:: python

    SESSION_COOKIE_AGE = 14 * 24 * 60 * 60
    SESSION_SAVE_EVERY_REQUEST = True


.. _config_email:

Configuring Email for QATrack+
------------------------------

QATrack+ email settings

QATrack+ has the ability to send emails :ref:`email notifications <qa_emails>`
when tests are at action or tolerance levels.  In order for this to function
you need access to an SMTP server that can send the emails for you.

In order to override the default settings, in your local_settings.py file you
should set the following variables appropriately.

Admin Email
~~~~~~~~~~~

Who should be emailed when internal QATrack+ errors occur:

.. code-block:: python

    ADMINS = (
        ('Admin Name', 'admin.email@yourplace.com'),
    )
    MANAGERS = ADMINS



Email host settings
~~~~~~~~~~~~~~~~~~~

* `EMAIL_HOST` should be set to the SMTP host you are using (e.g.
  'smtp.gmail.com' or 'smtp.mail.your.hospital')

* `EMAIL_HOST_USER`  this is the default username of the account to access the
  SMTP server

* `EMAIL_HOST_PASSWORD` this is the default account of the account to access
  the SMTP server

* `EMAIL_USE_TLS` set to True to use secure connection when connecting to the
  server

* `EMAIL_PORT` set to the port number to connect to the smtp server on (25 if
  `EMAIL_USE_TLS` is False,  587 if True)

* `EMAIL_FAIL_SILENTLY` set to False to see error tracebacks when sending an
  email fails. (should only be used for debugging)

Note that `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` can be set to None or ""
if no authentication is required.

An example of these settings for a secure connection is shown here (for gmail):

.. code-block:: python

    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_HOST_USER = 'randle.taylor@gmail.com'
    EMAIL_HOST_PASSWORD = 'my_very_secure_password'
    EMAIL_USE_TLS = True
    EMAIL_PORT = 587

and for an unsecured connection:

.. code-block:: python

    EMAIL_HOST = "MYHOSPITALSMTPSERVER"
    EMAIL_HOST_USER = None
    EMAIL_HOST_PASSWORD = None
    EMAIL_USE_TLS = False
    EMAIL_PORT = 25

Notification specific settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These settings allow you to override the default notification settings in your
local_settings.py file:


* `EMAIL_NOTIFICATION_SENDER` name to use in the email "From" address

* `EMAIL_NOTIFICATION_SUBJECT_TEMPLATE` allows you to override the default
  template to use for rendering the email subject line (see below)

* `EMAIL_NOTIFICATION_TEMPLATE` allows you to override the default template to
  use for rendering the email body (see below)

* (deprecated) `EMAIL_NOTIFICATION_USER` allows you to use a diferent user from
  the default set above (set to None to use `EMAIL_HOST_USER`).  This setting
  is no longer used, set `EMAIL_HOST_USER` instead.

* (deprecated) `EMAIL_NOTIFICATION_PWD` password to go along with
  `EMAIL_NOTIFICATION_USER`.  This setting is no longer used, set
  `EMAIL_HOST_PASSWORD` instead.


An example of these settings is shown here:

.. code-block:: python

    #-----------------------------------------------------------------------------
    # Email and notification settings
    EMAIL_NOTIFICATION_USER = None
    EMAIL_NOTIFICATION_PWD = None
    EMAIL_NOTIFICATION_SENDER = "Your Custom Name Here"
    EMAIL_NOTIFICATION_SUBJECT_TEMPLATE = "my_custom_subject_template.txt"
    EMAIL_NOTIFICATION_TEMPLATE = "my_custom_html_email.html"

Email & Subject templates
~~~~~~~~~~~~~~~~~~~~~~~~~

Emails are generated using `the Django template language
<https://docs.djangoproject.com/en/dev/ref/templates/api/>`__ with the
following context available:

* `test_list_instance` The TestListInstance object containing information about
  the test list and unit where the tests were being performed.

* `failing_tests` a `queryset
  <https://docs.djangoproject.com/en/dev/ref/models/querysets/>`__ of all tests
  that failed.

* `tolerance_tests` a `queryset
  <https://docs.djangoproject.com/en/dev/ref/models/querysets/>`__ of all tests
  that are at tolerance level.

To create your own templates, use the examples below as a starting point and
save them in the qatrack/notifications/templates/ directory and set the
filenames for the `TEMPLATE` settings above.

An example subject template is shown below

.. code-block:: django

    {{test_list_instance.work_completed|date:"DATE_FORMAT"}} - {{test_list_instance.unit_test_collection.unit.name }}, {{test_list_instance.test_list.name}} - {% if failing_tests %} Tests at Action: {{failing_tests.count}} {% endif %} {% if tolerance_tests %} Tests at Tolerance: {{tolerance_tests.count}} {% endif %}


The default HTML email template is shown here:

.. code-block:: html

    {% load comments %}
    <!doctype html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width" />
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <title>Notifications for {{test_list_instance.test_list.name}}</title>
        <style>
        /* -------------------------------------
            GLOBAL RESETS
        ------------------------------------- */
        img {
            border: none;
            -ms-interpolation-mode: bicubic;
            max-width: 100%; }

        body {
            background-color: #f6f6f6;
            font-family: sans-serif;
            -webkit-font-smoothing: antialiased;
            font-size: 14px;
            line-height: 1.4;
            margin: 0;
            padding: 0;
            -ms-text-size-adjust: 100%;
            -webkit-text-size-adjust: 100%; }

        table {
            border-collapse: separate;
            mso-table-lspace: 0pt;
            mso-table-rspace: 0pt;
            width: 100%; }
            table td {
            font-family: sans-serif;
            font-size: 14px;
            vertical-align: top; }

        th.header {
            text-align: right;
            margin-right: 10px;
            vertical-align: text-top;
        }

        table.test-table {
            text-align: left;
        }

        table.test-table thead tr th.action {
            text-align: center;
            font-size: 1.1em;
            background: #dd4b39;
            color: white;
        }

        table.test-table thead tr th.tolerance{
            text-align: center;
            font-size: 1.1em;
            background: #f39c12;
            color: white;
        }

        table.test-table td.value,
        table.test-table th.value{
            text-align: right;
        }

        table.test-table td.comment {
            text-align: left;
            font-style: italic;
        }

        table.test-table td.test,
        table.test-table th.test{
            text-align: left;
        }
        /* -------------------------------------
            BODY & CONTAINER
        ------------------------------------- */

        .body {
            background-color: #f6f6f6;
            width: 100%; }

        /* Set a max-width, and make it display as block so it will automatically stretch to that width, but will also shrink down on a phone or something */
        .container {
            display: block;
            Margin: 0 auto !important;
            /* makes it centered */
            max-width: 580px;
            padding: 10px;
            width: 580px; }

        /* This should also be a block element, so that it will fill 100% of the .container */
        .content {
            box-sizing: border-box;
            display: block;
            Margin: 0 auto;
            max-width: 580px;
            padding: 10px; }

        /* -------------------------------------
            HEADER, FOOTER, MAIN
        ------------------------------------- */
        .main {
            background: #ffffff;
            border-radius: 3px;
            width: 100%; }

        .wrapper {
            box-sizing: border-box;
            padding: 20px; }

        .content-block {
            padding-bottom: 10px;
            padding-top: 10px;
        }

        .footer {
            clear: both;
            Margin-top: 10px;
            text-align: center;
            width: 100%; }
            .footer td,
            .footer p,
            .footer span,
            .footer a {
            color: #999999;
            font-size: 12px;
            text-align: center; }

        /* -------------------------------------
            TYPOGRAPHY
        ------------------------------------- */
        h1,
        h2,
        h3,
        h4 {
            color: #000000;
            font-family: sans-serif;
            font-weight: 400;
            line-height: 1.4;
            margin: 0;
            Margin-bottom: 30px; }

        h1 {
            font-size: 35px;
            font-weight: 300;
            text-align: center;
            text-transform: capitalize; }

        p,
        ul,
        ol {
            font-family: sans-serif;
            font-size: 14px;
            font-weight: normal;
            margin: 0;
            Margin-bottom: 15px; }
            p li,
            ul li,
            ol li {
            list-style-position: inside;
            margin-left: 5px; }

        a {
            color: #3498db;
            text-decoration: underline; }

        /* -------------------------------------
            BUTTONS
        ------------------------------------- */
        .btn {
            box-sizing: border-box;
            width: 100%; }
            .btn > tbody > tr > td {
            padding-bottom: 15px; }
            .btn table {
            width: auto; }
            .btn table td {
            background-color: #ffffff;
            border-radius: 5px;
            text-align: center; }
            .btn a {
            background-color: #ffffff;
            border: solid 1px #3498db;
            border-radius: 5px;
            box-sizing: border-box;
            color: #3498db;
            cursor: pointer;
            display: inline-block;
            font-size: 14px;
            font-weight: bold;
            margin: 0;
            padding: 12px 25px;
            text-decoration: none;
            text-transform: capitalize; }

        .btn-primary table td {
            background-color: #3498db; }

        .btn-primary a {
            background-color: #3498db;
            border-color: #3498db;
            color: #ffffff; }

        /* -------------------------------------
            OTHER STYLES THAT MIGHT BE USEFUL
        ------------------------------------- */
        .last {
            margin-bottom: 0; }

        .first {
            margin-top: 0; }

        .align-center {
            text-align: center; }

        .align-right {
            text-align: right; }

        .align-left {
            text-align: left; }

        .clear {
            clear: both; }

        .mt0 {
            margin-top: 0; }

        .mb0 {
            margin-bottom: 0; }

        .preheader {
            color: transparent;
            display: none;
            height: 0;
            max-height: 0;
            max-width: 0;
            opacity: 0;
            overflow: hidden;
            mso-hide: all;
            visibility: hidden;
            width: 0; }

        .powered-by a {
            text-decoration: none; }

        hr {
            border: 0;
            border-bottom: 1px solid #f6f6f6;
            Margin: 20px 0; }

        /* -------------------------------------
            RESPONSIVE AND MOBILE FRIENDLY STYLES
        ------------------------------------- */
        @media only screen and (max-width: 620px) {
            table[class=body] h1 {
            font-size: 28px !important;
            margin-bottom: 10px !important; }
            table[class=body] p,
            table[class=body] ul,
            table[class=body] ol,
            table[class=body] td,
            table[class=body] span,
            table[class=body] a {
            font-size: 16px !important; }
            table[class=body] .wrapper,
            table[class=body] .article {
            padding: 10px !important; }
            table[class=body] .content {
            padding: 0 !important; }
            table[class=body] .container {
            padding: 0 !important;
            width: 100% !important; }
            table[class=body] .main {
            border-left-width: 0 !important;
            border-radius: 0 !important;
            border-right-width: 0 !important; }
            table[class=body] .btn table {
            width: 100% !important; }
            table[class=body] .btn a {
            width: 100% !important; }
            table[class=body] .img-responsive {
            height: auto !important;
            max-width: 100% !important;
            width: auto !important; }}

        /* -------------------------------------
            PRESERVE THESE STYLES IN THE HEAD
        ------------------------------------- */
        @media all {
            .ExternalClass {
            width: 100%; }
            .ExternalClass,
            .ExternalClass p,
            .ExternalClass span,
            .ExternalClass font,
            .ExternalClass td,
            .ExternalClass div {
            line-height: 100%; }
            .apple-link a {
            color: inherit !important;
            font-family: inherit !important;
            font-size: inherit !important;
            font-weight: inherit !important;
            line-height: inherit !important;
            text-decoration: none !important; }
            .btn-primary table td:hover {
            background-color: #34495e !important; }
            .btn-primary a:hover {
            background-color: #34495e !important;
            border-color: #34495e !important; } }

        </style>
    </head>
    <body class="">
        <table border="0" cellpadding="0" cellspacing="0" class="body">
        <tr>
            <td>&nbsp;</td>
            <td class="container">
            <div class="content">

                <!-- START CENTERED WHITE CONTAINER -->
                <span class="preheader">Notifications for {{test_list_instance.test_list.name}}</span>
                <table class="main">

                <!-- START MAIN CONTENT AREA -->
                <tr>
                    <td class="wrapper">
                    <table border="0" cellpadding="0" cellspacing="0">
                        <tr>
                        <td>
                            <p>Hello</p>
                            <p>
                            You are receiving this notice because one or more tests were at tolerance or action levels
                            for the following test list instance:
                            </p>
                            <table>
                            <tr>
                                <th class="header">
                                Test List:
                                </th>
                                <td>
                                {{test_list_instance.test_list.name}}
                                </td>
                            </tr>
                            <tr>
                                <th class="header">
                                Unit:
                                </th>
                                <td>
                                {{test_list_instance.unit_test_collection.unit.name}}
                                </td>
                            </tr>
                            <tr>
                                <th class="header">
                                Date:
                                </th>
                                <td>
                                {{ test_list_instance.work_completed }}
                                </td>
                            </tr>
                            <tr>
                                <th class="header">
                                Link:
                                </th>
                                <td>
                                <a href="{% if 'http' not in domain %}http://{% endif %}{{ domain }}{{ test_list_instance.get_absolute_url }}"
                                    title="Click to view on the site"
                                >
                                    {% if 'http' not in domain %}http://{% endif %}{{ domain }}{{ test_list_instance.get_absolute_url }}
                                </a>
                                </td>
                            </tr>
                            {% if test_list_instance.comments.exists %}
                                <tr>
                                <th class="header">Comments:</th>
                                <td>
                                    {% render_comment_list for test_list_instance %}
                                </td>
                                </tr>
                            {% endif %}
                            </table>
                            <table class="test-table">
                            <thead>
                                <tr>
                                <th class="action" colspan="4">
                                    Failing Tests
                                </th>
                                </tr>
                                <tr>
                                <th class="test">Test</th>
                                <th class="value">Value</th>
                                <th class="value">Reference</th>
                                <th class="value">Tolerance</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for test_instance in failing_tests %}
                                <tr>
                                    <td class="test">{{test_instance.unit_test_info.test.name}}</td>
                                    <td class="value">{{test_instance.value_display}}</td>
                                    <td class="value">{{test_instance.reference}}</td>
                                    <td class="value">{{test_instance.tolerance}}</td>
                                </tr>
                                {% if test_instance.comment %}
                                    <tr>
                                    <td class="comment" colspan="4">
                                        {{ test_instance.comment }}
                                    </td>
                                    </tr>
                                {% endif %}
                                {% endfor %}
                            </tbody>
                            </table>
                            <table class="test-table">
                            <thead>
                                <tr>
                                <th class="tolerance" colspan="4">
                                    Tests at Tolerance
                                </th>
                                </tr>
                                <tr>
                                <th class="test">Test</th>
                                <th class="value">Value</th>
                                <th class="value">Reference</th>
                                <th class="value">Tolerance</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for test_instance in tolerance_tests %}
                                <tr>
                                    <td class="test">{{test_instance.unit_test_info.test.name}}</td>
                                    <td class="value">{{test_instance.value_display}}</td>
                                    <td class="value">{{test_instance.reference}}</td>
                                    <td class="value">{{test_instance.tolerance}}</td>
                                </tr>
                                {% if test_instance.comment %}
                                    <tr>
                                    <td class="comment" colspan="4">
                                        {{ test_instance.comment }}
                                    </td>
                                    </tr>
                                {% endif %}
                                {% endfor %}
                            </tbody>
                            </table>
                        </td>
                        </tr>
                    </table>
                    </td>
                </tr>

                <!-- END MAIN CONTENT AREA -->
                </table>

                <!-- START FOOTER -->
                <div class="footer">
                <table border="0" cellpadding="0" cellspacing="0">
                    <tr>
                    <td class="content-block">
                        <span class="apple-link"></span>
                    </td>
                    </tr>
                    <tr>
                    <td class="content-block powered-by">
                        Sent by QATrack+
                    </td>
                    </tr>
                </table>
                </div>
                <!-- END FOOTER -->

            <!-- END CENTERED WHITE CONTAINER -->
            </div>
            </td>
            <td>&nbsp;</td>
        </tr>
        </table>
    </body>
    </html>

An example plain text email template is shown below

.. code-block:: text

    === Notifications for {{test_list_instance.test_list.name}} ===

    Test List : {{test_list_instance.test_list.name}}
    Unit      : {{test_list_instance.unit_test_collection.unit.name}}
    Date      : {{test_list_instance.work_completed }}

    {% if failing_tests %}
    Failing Tests
    =============
    {% for test_instance in failing_tests %}
        Test  : {{test_instance.unit_test_info.test.name}}
        Value : {{test_instance.value_display}}
        Ref.  : {{test_instance.reference}}
        Tol.  : {{test_instance.tolerance}}
    {% endfor %}
    {% endif %}

    {% if tolerance_tests %}
    Tests at Tolerance
    ==================
    {% for test_instance in tolerance_tests %}
        Test  : {{test_instance.unit_test_info.test.name}}
        Value : {{test_instance.value_display}}
        Ref.  : {{test_instance.reference}}
        Tol.  : {{test_instance.tolerance}}
    {% endfor %}
    {% endif %}


.. _settings_ad:

Active Directory Settings
~~~~~~~~~~~~~~~~~~~~~~~~~

QATrack+ allows you to use an Active Directory (AD) server for User
authentication.  In order to use Active Directory you need to set up the
following settings:

AUTHENTICATION_BACKENDS
.......................

In order to use the AD backend, you need to set the `AUTHENTICATION BACKENDS` setting as follows:

.. code-block:: python

    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'qatrack.accounts.backends.ActiveDirectoryGroupMembershipSSLBackend',
    )

General AD Settings
...................


.. code-block:: python

    AD_DNS_NAME = 'ad.subdomain.maindomain.on.ca'  # DNS Name
    AD_LU_ACCOUNT_NAME = "sAMAccountName"  # AD Lookup account name property
    AD_LU_MAIL = "mail"  # AD Lookup account email property
    AD_LU_SURNAME = "sn"  # AD Lookup account surname property
    AD_LU_GIVEN_NAME = "givenName"  # AD Lookup account given name property
    AD_LU_MEMBER_OF = "memberOf"  # AD Lookup group membership property

    AD_SEARCH_DN = ""  # eg "dc=ottawahospital,dc=on,dc=ca"
    AD_NT4_DOMAIN = ""  # Network domain that AD server is part of

    AD_MEMBERSHIP_REQ = []  # Currently not implemented! See issue #360
                            # optional list of groups that user must be a part of in order to create account
                            # eg ["*TOHCC - All Staff | Tout le personnel  - CCLHO"]

    AD_CERT_FILE = '/path/to/your/cert.txt'

    AD_DEBUG = False  # turn on active directory loggin
    AD_DEBUG_FILE = None  # log file path for debugging AD connection issues

    AD_CLEAN_USERNAME_STRING = ''  # if your AD usernames are returned as e.g. "foo/jsmith" then
                                   # setting `AD_CLEAN_USERNAME_STRING = 'foo/'` will strip the `foo/` prefix
                                   # off the username, so the QATrack+ username will just be 'jsmith'

    AD_CLEAN_USERNAME = None  # define a function called AD_CLEAN_USERNAME in local_settings.py if you
                              # wish to clean usernames before sending to ldap server e.g.
                              # def AD_CLEAN_USERNAME(username): return username.lower()


Non-SSL AD Connection Settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If using a non-SSL connection use these

.. code-block:: python

    AD_LDAP_PORT = 389
    AD_LDAP_URL = 'ldap://%s:%s' % (AD_DNS_NAME, AD_LDAP_PORT)
    AD_LDAP_USER = ''
    AD_LDAP_PW = ''


SSL AD Connection Settings
^^^^^^^^^^^^^^^^^^^^^^^^^^


If using SSL use these:

.. code-block:: python

    AD_LDAP_PORT = 636
    AD_LDAP_URL = 'ldaps://%s:%s' % (AD_DNS_NAME,AD_LDAP_PORT)
    AD_LDAP_USER = ''
    AD_LDAP_PW = ''


More information on Active Directory is available here: :ref:`Active Directory
<active_directory>`.
