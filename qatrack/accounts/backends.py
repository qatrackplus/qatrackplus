import ldap
from django.conf import settings
from django.contrib.auth.models import User


#stripped down version of http://djangosnippets.org/snippets/901/
class ActiveDirectoryGroupMembershipSSLBackend:

    #----------------------------------------------------------------------
    def authenticate(self, username=None, password=None):
        debug = None
        if settings.AD_DEBUG_FILE and settings.AD_DEBUG:
            debug = open(settings.AD_DEBUG_FILE,'w')
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
                    debug = open(settings.AD_DEBUG_FILE,'a')
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
                result = l.search_ext_s(settings.AD_SEARCH_DN, ldap.SCOPE_SUBTREE, "sAMAccountName=%s" % username, settings.AD_SEARCH_FIELDS)[0][1]

                # get personal info
                mail = result.get("mail", ["mail@example.com"])[0]
                last_name = result.get("sn", [username])[0]
                first_name = result.get("givenName", [username])[0]

                l.unbind_s()

                user = User(username=username, first_name=first_name, last_name=last_name, email=mail)

            except Exception, e:
                if debug:
                    print >>debug, "Exception:"
                    print >>debug, e
                return None

            user.is_staff = False
            user.is_superuser = False
            user.set_password('ldap authenticated')
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
