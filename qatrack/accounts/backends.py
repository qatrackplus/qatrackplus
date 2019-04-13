from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

import ldap


#stripped down version of http://djangosnippets.org/snippets/901/
class ActiveDirectoryGroupMembershipSSLBackend:

    #----------------------------------------------------------------------
    def authenticate(self, username=None, password=None):
        debug = None
        if settings.AD_DEBUG_FILE and settings.AD_DEBUG:
            debug = open(settings.AD_DEBUG_FILE, 'w')
            print >>debug, "authenticate user %s" % username

        try:
            if len(password) == 0:
                return None

            #ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, settings.AD_CERT_FILE)
            if debug:
                print >>debug, "\tinitialize..."
            l = ldap.initialize(settings.AD_LDAP_URL)
            l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            binddn = "%s@%s" % (username, settings.AD_NT4_DOMAIN)
            if debug:
                print >>debug, "\tbind..."
            l.simple_bind_s(binddn, password)
            l.unbind_s()

            if debug:
                print >>debug, "\tsuccessfully authenticated: %s" % username
            return self.get_or_create_user(username, password)

        except Exception, e:
            if debug:
                print >>debug, "\tException occured "
                print >>debug, e

    #----------------------------------------------------------------------
    def get_or_create_user(self, username, password):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:

            try:
                debug = None
                if settings.AD_DEBUG_FILE and settings.AD_DEBUG:
                    debug = open(settings.AD_DEBUG_FILE, 'a')
                    print >>debug, "create user %s" % username

                #ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, settings.AD_CERT_FILE)
                ldap.set_option(ldap.OPT_REFERRALS, 0)  # DO NOT TURN THIS OFF OR SEARCH WON'T WORK!

                # initialize
                if debug:
                    print >>debug, "\tinitialize..."
                l = ldap.initialize(settings.AD_LDAP_URL)
                l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

                # bind
                if debug:
                    print >>debug, "\tbind..."
                binddn = "%s@%s" % (username, settings.AD_NT4_DOMAIN)
                l.bind_s(binddn, password)

                # search
                if debug:
                    print >>debug, "\tsearch..."
                result = l.search_ext_s(settings.AD_SEARCH_DN, ldap.SCOPE_SUBTREE, "%s=%s" % (settings.AD_LU_ACCOUNT_NAME, username), settings.AD_SEARCH_FIELDS)[0][1]

                # get personal info
                mail = result.get(settings.AD_LU_MAIL, ["mail@example.com"])[0]
                last_name = result.get(settings.AD_SURNAME, [username])[0]
                first_name = result.get(settings.AD_LU_GIVEN_NAME, [username])[0]

                l.unbind_s()

                user = User(username=username, first_name=first_name, last_name=last_name, email=mail)

            except Exception, e:
                if debug:
                    print >>debug, "Exception:"
                    print >>debug, e
                return None

            user.is_staff = False
            user.is_superuser = False
            user.set_unusable_password()
            user.save()
            if debug:
                print >>debug, "User created: %s" % username
        return user

    #----------------------------------------------------------------------
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class WindowsIntegratedAuthenticationBackend(ModelBackend):

    # Create a User object if not already in the database?
    create_unknown_user = True

    def authenticate(self, remote_user):
        """
        The username passed as ``remote_user`` is considered trusted.  This
        method simply returns the ``User`` object with the given username,
        creating a new ``User`` object if ``create_unknown_user`` is ``True``.

        Returns None if ``create_unknown_user`` is ``False`` and a ``User``
        object with the given username is not found in the database.
        """
        if not remote_user:
            return
        username = self.clean_username(remote_user)

        # Note that this could be accomplished in one try-except clause, but
        # instead we use get_or_create when creating unknown users since it has
        # built-in safeguards for multiple threads.
        if self.create_unknown_user:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user = self.configure_user(user)
        else:
            try:
                user = User.objects.get(user)
            except User.DoesNotExist:
                pass
        return user

    def clean_username(self, username):
        """
        Performs any cleaning on the "username" prior to using it to get or
        create the user object.  Returns the cleaned username.

        By default, returns the username unchanged.
        """
        return username.replace(settings.CLEAN_USERNAME_STRING, "")

    def configure_user(self, user):
        """
        Configures a user after creation and returns the updated user.

        By default, returns the user unmodified.
        """
        try:
            ldap.set_option(ldap.OPT_REFERRALS, 0)  # DO NOT TURN THIS OFF OR SEARCH WON'T WORK!

            # initialize
            l = ldap.initialize(settings.AD_LDAP_URL)

            # bind
            binddn = "%s@%s" % (settings.AD_LDAP_USER, settings.AD_NT4_DOMAIN)
            l.bind_s(binddn, settings.AD_LDAP_PW)

            # search
            result = l.search_ext_s(settings.AD_SEARCH_DN, ldap.SCOPE_SUBTREE, "%s=%s" % (settings.AD_LU_ACCOUNT_NAME, user), settings.AD_SEARCH_FIELDS)[0][1]
            l.unbind_s()

            # get personal info
            user.email = result.get(settings.AD_LU_MAIL, [None])[0]
            user.last_name = result.get(settings.AD_LU_SURNAME, [None])[0]
            user.first_name = result.get(settings.AD_LU_GIVEN_NAME, [None])[0]

        except Exception:
            return None

        user.is_staff = False
        user.is_superuser = False
        user.set_unusable_password()

        user.save()
        return user
