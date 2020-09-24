.. _auth_backends:

Authentication Backends
=======================

QATrack+ has a few different methods of authenticating users:

* The built in Django backend. No additional configuration is required but
  users and their group memberships need to be managed manually.
* :ref:`Active Directory <active_directory>`.  Use your hospitals AD system for managing
  users and groups.
* :ref:`Active Directory Federiation Services <auth_adfs>`.  Use your hospitals AD FS system for managing
  users and groups.

.. _active_directory:

Active Directory
----------------

Using an existing Active Directory server to do your user authentication is a
great way to simply the management of users for your QATrack+ system.  It's
especially convenient for your users that they don't have to remember "yet
another password" and can simply use their network logon.  QATrack+ comes with
an Active Directory backend and it's configuration will be described below.

Installation of python-ldap
...........................

Windows
~~~~~~~

If you happen to be on a Windows system with Visual Studio installed, you
should just be able to do `pip install python-ldap` and have the latest version of
the pyldap package installed.  Otherwise,  there are binaries available on this
page: https://www.lfd.uci.edu/~gohlke/pythonlibs/#python-ldap.  Download the binary
relevant to your Python 3 installation (e.g.
python_ldap‑3.3.1‑cp36‑cp36m‑win_amd64.whl) and then pip install it:

.. code-block:: console

    pip install C:\path\to\python_ldap‑3.3.1‑cp36‑cp36m‑win_amd64.whl


To confirm your installation is working, activate your virtual env

.. code-block:: console

    cd C:\deploy
    .\venvs\qatrack3\scripts\activate
    python -c "import ldap; print(ldap.__version__)"

If that commands prints the ldap version then ldap is installed correctly.

Linux
~~~~~


There are some pre-requisistes that need to be installed before python-ldap. 

At the time of writing on Ubuntu this looks like:

.. code-block:: console

    sudo apt-get install build-essential python3-dev python2.7-dev \
        libldap2-dev libsasl2-dev slapd ldap-utils

    source ~/venvs/qatrack3/bin/activate
    pip install python-ldap

See https://www.python-ldap.org/en/latest/installing.html for more details.


Configuring QATrack+ to use your Active Directory Server
........................................................

Copy the following lines to your `local_settings.py` file:

.. code-block:: python

    #-----------------------------------------------------------------------------
    # Authentication backend settings
    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'qatrack.accounts.backends.ActiveDirectoryGroupMembershipSSLBackend',
    )

    # active directory settings (not required if only using ModelBackend
    AD_DNS_NAME = 'your.ad.server.yourhospital.com'

    # If using non-SSL use these
    AD_LDAP_PORT = 389
    AD_LDAP_URL = 'ldap://%s:%s' % (AD_DNS_NAME, AD_LDAP_PORT)

    # If using SSL use these:
    # AD_LDAP_PORT=636
    # AD_LDAP_URL='ldaps://%s:%s' % (AD_DNS_NAME,AD_LDAP_PORT)

    AD_CERT_FILE = None  # AD_CERT_FILE='/path/to/your/cert.txt'

    AD_SEARCH_DN = "dc=yourdomain,dc=yourhospital,dc=com"
    AD_NT4_DOMAIN = "YOURDOMAIN"  # Network domain that AD server is part of

    AD_SEARCH_FIELDS = ['mail', 'givenName', 'sn', 'sAMAccountName', 'memberOf']

    AD_DEBUG_FILE = "C:/deploy/qatrackplus/logs/ad_log.txt"
    AD_DEBUG = False # set to True and restart QATrack+ CherryPy Service if you need to debug AD Connection

You will also obviously have to modify `AD_DNS_NAME1, `AD_SEARCH_DN` and
`AD_NT4_DOMAIN` to suit your own Active Directory setup.  The complete set of
Active Directory settings are described here: :ref:`Active Directory Settings
<settings_ad>`.

After you have saved that file, you will need to restart your application
server (or for example your CherryPy service).

.. _auth_adfs:

Active Directory Federation Services (ADFS)
-------------------------------------------

As of version 0.3.1 comes with an ADFS backend for Single Sign On (SSO).  This
can provide a convenient way for your users to log into QATrack+ using their
hospital network login.

There are two backends you can potentially use for using ADFS for SSO.  There
is the raw `django_adfs.backends.AdfsAuthCodeBackend` which you can read more
about at https://django-auth-adfs.readthedocs.io/en/latest/settings_ref.html
and there is the `qatrack.accounts.backends.QATrackAdfsAuthCodeBackend` which
is a wrapper around the `AdfsAuthCodeBackend` with some QATrack+ specific
functionality added. In order to enable one of these backends you need to set your
`AUTHENTICATION_BACKENDS` setting like:

.. code:: python

    AUTHENTICATION_BACKENDS = [
        'qatrack.accounts.backends.QATrackAccountBackend',
        'qatrack.accounts.backends.QATrackAdfsAuthCodeBackend',
        # or comment above and uncomment below
        # 'django_adfs.backends.AdfsAuthCodeBackend'
    ]


Configuring your ADFS Server
............................

Please see the following guides to configure your ADFS Server to allow
access for QATrack+:

.. toctree::
    :maxdepth: 1

    adfs_server_2016
    adfs_server_2012


.. _auth_adfs_settings:

Configuring QATrack+ to use ADFS
................................

Copy the following lines to your `local_settings.py` file:

.. code:: python

    AUTHENTICATION_BACKENDS = [
        'qatrack.accounts.backends.QATrackAccountBackend',
        'qatrack.accounts.backends.QATrackAdfsAuthCodeBackend',
    ]

    # AD FS settings.
    AUTH_ADFS = {
        "SERVER": "some.adfs.server.com",
        "CLIENT_ID": "qatrackplus",
        "RELYING_PARTY_ID": "https://your.qatrackserver.com",
        "AUDIENCE": "https://your.qatrackserver.com",
        "CLAIM_MAPPING": {
            "first_name": "given_name",
            "last_name": "family_name",
            "email": "email"
        },
        "USERNAME_CLAIM": "winaccountname",
        "GROUPS_CLAIM": "group",
    }


If you require a different configuration for some reason, more options and settings
are described in https://django-auth-adfs.readthedocs.io/en/latest/settings_ref.html


Mapping Active Directory Groups to QATrack+ Groups
--------------------------------------------------

You can have your users automatically added to one or more :ref:`QATrack+
groups <auth_groups>` based on their Active Directory Group memberships.  For
more information on configuring this see :ref:`Active Directory Group to
QATrack+ Groups Map <auth_ad_groups>`.


