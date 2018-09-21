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
should just be able to do `pip install python-ldap` and have the latest version
of the python-ldap package installed.  Otherwise, download and run the
appropriate python-ldap .msi installer from the `LDAP PyPi page
<https://pypi.org/project/python-ldap/>`__.  Documentation for python-ldap 
is avaialable on the web: https://www.python-ldap.org/en/latest/.


That will install python-ldap to the main system Python installation, but
assuming you're using virtualenv, you'll need to copy the LDAP package to your
virtualenv.

Open a Git Bash shell and enter the following command (adjusting paths as
required) to copy the ldap install to your virtual environment:

`cp -r /c/Python36/lib/site-packages/ldap* /c/deploy/venvs/qatrack/lib/site-packages/`

You can also feel free to use Windows Explorer or CMD to copy the files!

To confirm your installation is working, activate your virtual env 

`source /c/deploy/venvs/qatrack/Scripts/activate`

and then type

`python -c "import ldap; print ldap.__version__"` 

If that commands prints the ldap version then ldap is installed correctly.

Configuring QATrack+ to use your Active Directory Server
--------------------------------------------------------

Copy the following lines to your local\_settings.py file:

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

You will also obviously have to modify AD\_DNS\_NAME, AD\_SEARCH\_DN and
AD\_NT4\_DOMAIN to suit your own Active Directory setup.  The copmlete set of
Active Directory settings are described here: :ref:`Active Directory Settings
<settings_ad>`.

After you have saved that file, you will need to restart your application
server (or for example your CherryPy service).
