from django.contrib.auth.hashers import BasePasswordHasher

try:
    from .settings import *  # noqa: F403,F401
except ImportError:
    pass

try:
    from .local_settings import *  # noqa: F403,F401
except ImportError:
    pass

NOTIFICATIONS_ON = False
DEFAULT_NUMBER_FORMAT = None
DEBUG = False
SELENIUM_VIRTUAL_DISPLAY = False # Set to True to use headless browser for testing (requires xvfb)
AD_CLEAN_USERNAME = None
HTTP_OR_HTTPS = "http"
REVIEW_BULK = True
TIME_ZONE = 'America/Toronto'


class SimplePasswordHasher(BasePasswordHasher):
    """A simple hasher inspired by django-plainpasswordhasher"""

    algorithm = "dumb"  # This attribute is needed by the base class.

    def salt(self):
        return ""

    def encode(self, password, salt):
        return "dumb$$%s" % password

    def verify(self, password, encoded):
        algorithm, hash = encoded.split("$$", 1)
        assert algorithm == "dumb"
        return password == hash

    def safe_summary(self, encoded):
        """This is a decidedly unsafe version.

        The password is returned in the clear.
        """
        return {"algorithm": "dumb", "hash": encoded.split("$", 2)[2]}


PASSWORD_HASHERS = ("qatrack.test_settings.SimplePasswordHasher",)

AUTHENTICATION_BACKENDS = ['qatrack.accounts.backends.QATrackAccountBackend']

try:
    from .local_test_settings import *  # noqa: F403,F401
except ImportError:
    pass
