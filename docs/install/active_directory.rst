.. _active_directory:

Active Directory
================

Using an existing Active Directory server to do your user authentication is a
great way to simply the management of users for your QATrack+ system.  It's
especially convenient for your users that they don't have to remember "yet
another password" and can simply use their network logon.  QATrack+ comes with
an Active Directory backend and it's configuration will be described below.

Installation of python-ldap
---------------------------

If you happen to be on a Windows system with Visual Studio installed, you
should just be able to do `pip install pyldap` and have the latest version of
the pyldap package installed.  Otherwise,  there are binaries available on this
page: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyldap.  Download the binary
relevant to your Python 3 installation (e.g.
pyldap‑2.4.45‑cp36‑cp36m‑win_amd64.whl) and then pip install it:

.. code-block:: console

    pip install C:\path\to\pyldap‑2.4.45‑cp36‑cp36m‑win_amd64.whl


To confirm your installation is working, activate your virtual env

.. code-block:: console

    cd C:\deploy
    .\venvs\qatrack3\scripts\activate
    python -c "import ldap; print ldap.__version__"

If that commands prints the ldap version then ldap is installed correctly.


Configuring QATrack+ to use your Active Directory Server
--------------------------------------------------------

Copy the following lines to your `local_settings.py` file:

.. code-block:: python

    #-----------------------------------------------------------------------------
    # Account settings
    # a list of group names to automatically add users to when they sign up
    DEFAULT_GROUP_NAMES = ["Therapists"]  # Replace Therapists with whatever group name you want

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

    AD_SEARCH_DN = "dc=yourdomain,dc=yourhospital,dc=com"
    AD_NT4_DOMAIN = "YOURDOMAIN"  # Network domain that AD server is part of

    AD_SEARCH_FIELDS = ['mail', 'givenName', 'sn', 'sAMAccountName', 'memberOf']
    AD_MEMBERSHIP_REQ = []

    AD_DEBUG_FILE = "C:/deploy/qatrackplus/logs/ad_log.txt"
    AD_DEBUG = False # set to True and restart QATrack+ CherryPy Service if you need to debug AD Connection

You will also obviously have to modify `AD_DNS_NAME1, `AD_SEARCH_DN` and
`AD_NT4_DOMAIN` to suit your own Active Directory setup.  The complete set of
Active Directory settings are described here: :ref:`Active Directory Settings
<settings_ad>`.

After you have saved that file, you will need to restart your application
server (or for example your CherryPy service).
