try:
    import ldap
except ImportError:
    pass

import logging

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group, User


class QATrackAccountBackend(ModelBackend):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger('auth.QATrackAccountBackend')

    def authenticate(self, request, username=None, password=None):
        self.logger.info("Attempting to authenticate %s" % username)
        username = self.clean_username(username)
        self.logger.info("Cleaned username: %s" % username)

        user = super().authenticate(request, username=username, password=password)
        if user:
            self.logger.info("Successfully authenticated user: %s" % username)
        else:
            self.logger.info("Authentication failed for user: %s" % username)

        return user

    def clean_username(self, username):
        """
        Performs any cleaning on the "username" prior to using it to get or
        create the user object.  Returns the cleaned username.

        By default, returns the username unchanged.
        """
        if settings.ACCOUNTS_CLEAN_USERNAME and callable(settings.ACCOUNTS_CLEAN_USERNAME):
            return settings.ACCOUNTS_CLEAN_USERNAME(username)
        return username.replace(settings.CLEAN_USERNAME_STRING, "")


# stripped down version of http://djangosnippets.org/snippets/901/
class ActiveDirectoryGroupMembershipSSLBackend:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger('auth.ActiveDirectoryGroupMembershipSSLBackend')

        ldap.set_option(ldap.OPT_REFERRALS, 0)  # DO NOT TURN THIS OFF OR SEARCH WON'T WORK!
        if settings.AD_CERT_FILE:
            self.logger.debug("Setting TLS CERTFILE %s." % settings.AD_CERT_FILE)
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, settings.AD_CERT_FILE)

    def authenticate(self, request, username=None, password=None):

        self.logger.info("Attempting to authenticate %s" % username)
        username = self.clean_username(username)
        self.logger.info("Cleaned username: %s" % username)

        try:
            if len(password) == 0:
                self.logger.info("Failed to authenticate user. No password provided.")
                return None

            self.logger.debug("Initializing with ldap url=%s" % settings.AD_LDAP_URL)
            l = ldap.initialize(settings.AD_LDAP_URL)
            l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

            binddn = "%s@%s" % (username, settings.AD_NT4_DOMAIN)
            self.logger.debug("Binding with binddn=%s" % binddn)
            l.simple_bind_s(binddn, password)

            user_attrs = self.get_user_attrs(l, username)
            if settings.AD_MEMBERSHIP_REQ:
                if len(set(settings.AD_MEMBERSHIP_REQ) & set(user_attrs['member_of'])) == 0:
                    self.logger.info(
                        "successfully authenticated: %s but they don't belong to a required group (%s)" %
                        (username, settings.AD_MEMBERSHIP_REQ)
                    )
                    return None

            self.logger.debug("successfully authenticated: %s" % username)

            return self.get_or_create_user(username, user_attrs)

        except ldap.INVALID_CREDENTIALS:
            self.logger.info("Invalid username or password for user: %s" % username)
            return None
        except ldap.SERVER_DOWN:
            self.logger.exception("Unable to contact LDAP server")
        except Exception:
            self.logger.exception("Exception occured while trying to authenticate %s" % username)
            return None
        finally:
            try:
                l.unbind_s()
            except Exception:
                pass

    def get_user_attrs(self, con, username):

        self.logger.debug("Searching active directory for user attributes with search DN: %s" % settings.AD_SEARCH_DN)

        result = con.search_ext_s(
            settings.AD_SEARCH_DN,
            ldap.SCOPE_SUBTREE,
            "%s=%s" % (settings.AD_LU_ACCOUNT_NAME, username),
            settings.AD_SEARCH_FIELDS,
        )[0][1]

        email = result.get(settings.AD_LU_MAIL, [""])[0]
        last_name = result.get(settings.AD_LU_SURNAME, [""])[0]
        first_name = result.get(settings.AD_LU_GIVEN_NAME, [""])[0]
        email = email.decode('utf-8') if isinstance(email, bytes) else email
        last_name = last_name.decode('utf-8') if isinstance(last_name, bytes) else last_name
        first_name = last_name.decode('utf-8') if isinstance(last_name, bytes) else last_name
        attrs = {
            'email': email,
            'last_name': last_name,
            'first_name': first_name,
        }

        member_of = result.get(settings.AD_LU_MEMBER_OF, [""])[0]
        if isinstance(member_of, bytes):
            member_of = member_of.decode()

        # member of comes in format like CN=TestGroup,CN=Users,DC=foo,DC=example,DC=com
        member_of = [x.split("=")[1] for x in member_of.split(",") if "cn=" in x.lower()]
        attrs['member_of'] = member_of

        return attrs

    def get_or_create_user(self, username, user_attrs):

        try:
            self.logger.debug("Looking for existing user with username: %s" % username)
            user = User.objects.get(username=username)
            self.logger.debug("Found existing user with username: %s" % username)
        except User.DoesNotExist:
            self.logger.debug("No existing user with username: %s" % username)
            user = User(username=username, is_staff=False, is_superuser=False)
            user.set_unusable_password()
            try:
                user.save()
                self.logger.info("Created user with username: %s" % username)
            except Exception:
                self.logger.info("Creation of user failed")
                return None

        self.update_user_attrs(user, user_attrs)

        return user

    def update_user_attrs(self, user, user_attrs):

        self.logger.info("Updating user info for %s" % user.username)

        # get personal info
        user.email = user_attrs['email'] or user.email
        user.last_name = user_attrs['last_name'] or user.last_name
        user.first_name = user_attrs['first_name'] or user.first_name

        user_groups = user.groups.all()
        for ad_group in user_attrs['member_of']:
            if ad_group in settings.AD_GROUP_MAP:
                group = Group.objects.filter(name=settings.AD_GROUP_MAP[ad_group]).first()
                if group and group not in user_groups:
                    user.groups.add(group)
                    self.logger.info("Add %s to group %s" % (user.username, group.name))

        user.save()

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def clean_username(self, username):
        """
        Performs any cleaning on the "username" prior to using it to get or
        create the user object.  Returns the cleaned username.

        By default, returns the username unchanged.
        """
        if settings.AD_CLEAN_USERNAME and callable(settings.AD_CLEAN_USERNAME):
            return settings.AD_CLEAN_USERNAME(username)
        return username.replace(
            settings.CLEAN_USERNAME_STRING, ""
        ).replace(
            settings.AD_CLEAN_USERNAME_STRING, ""
        )


class WindowsIntegratedAuthenticationBackend(ModelBackend):

    # Create a User object if not already in the database?
    create_unknown_user = True

    def authenticate(self, request, username=None):
        """
        The username passed is considered trusted.  This
        method simply returns the ``User`` object with the given username,
        creating a new ``User`` object if ``create_unknown_user`` is ``True``.

        Returns None if ``create_unknown_user`` is ``False`` and a ``User``
        object with the given username is not found in the database.
        """
        if not username:
            return
        username = self.clean_username(username)

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
        if settings.AD_CLEAN_USERNAME and callable(settings.AD_CLEAN_USERNAME):
            return settings.AD_CLEAN_USERNAME(username)
        return username.replace(settings.CLEAN_USERNAME_STRING, "").replace(settings.AD_CLEAN_USERNAME_STRING, "")

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
            result = l.search_ext_s(
                settings.AD_SEARCH_DN,
                ldap.SCOPE_SUBTREE,
                "%s=%s" % (settings.AD_LU_ACCOUNT_NAME, user),
                settings.AD_SEARCH_FIELDS,
            )[0][1]
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
