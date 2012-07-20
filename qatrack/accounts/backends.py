import ldap
from qatrack import settings
from django.contrib.auth.models import User, Group

#stripped down version of http://djangosnippets.org/snippets/901/
class ActiveDirectoryGroupMembershipSSLBackend:

    #----------------------------------------------------------------------
    def authenticate(self,username=None,password=None):
        try:
            if len(password) == 0:
                return None

            #ldap.set_option(ldap.OPT_X_TLS_CACERTFILE,settings.AD_CERT_FILE)
            l = ldap.initialize(settings.AD_LDAP_URL)
            l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            binddn = "%s@%s" % (username,settings.AD_NT4_DOMAIN)
            l.simple_bind_s(binddn,password)
            l.unbind_s()
            return self.get_or_create_user(username,password)

        except ImportError:
            pass
        except ldap.INVALID_CREDENTIALS:
            pass
    #----------------------------------------------------------------------
    def get_or_create_user(self, username, password):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:

            try:

                #ldap.set_option(ldap.OPT_X_TLS_CACERTFILE,settings.AD_CERT_FILE)
                ldap.set_option(ldap.OPT_REFERRALS,0) # DO NOT TURN THIS OFF OR SEARCH WON'T WORK!

                # initialize
                l = ldap.initialize(settings.AD_LDAP_URL)
                l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

                # bind
                binddn = "%s@%s" % (username,settings.AD_NT4_DOMAIN)
                l.bind_s(binddn,password)

                # search
                result = l.search_ext_s(settings.AD_SEARCH_DN,ldap.SCOPE_SUBTREE,"sAMAccountName=%s" % username,settings.AD_SEARCH_FIELDS)[0][1]

                # Validate that they are a member of review board group
                membership = result.get('memberOf',None)

                # get personal info
                mail = result.get("mail",[None])[0]
                last_name = result.get("sn",[None])[0]
                first_name = result.get("givenName",[None])[0]


                l.unbind_s()

                user = User(username=username,first_name=first_name,last_name=last_name,email=mail)

            except Exception, e:
                return None

            user.is_staff = False
            user.is_superuser = False
            user.set_password('ldap authenticated')
            user.save()
        return user

    #----------------------------------------------------------------------
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

