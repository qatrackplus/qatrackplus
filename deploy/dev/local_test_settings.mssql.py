# Test-specific settings for QATrack+ - SQL Server variant
# Copy this file to qatrack/local_test_settings.py and customize as needed
#
# Requires the `mssql` extra: uv sync --extra mssql

DEBUG = True
TEMPLATE_DBG = True

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'USER': 'your_mssql_user',
        'PASSWORD': 'your_mssql_password',
        'HOST': 'hostname',
        'PORT': '1433',  # SQL Server default
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
        },
        # Database Name not needed for test environments.
        # User must be created on the host server with admin and dbcreator
        # rights. If you'd rather use Windows-integrated auth instead of a
        # SQL login, remove USER/PASSWORD above and add:
        #     'Trusted_Connection': 'yes',
    }
}
DATABASES['readonly'] = DATABASES['default']

# Test-specific settings
NOTIFICATIONS_ON = False
DEFAULT_NUMBER_FORMAT = None
AD_CLEAN_USERNAME = None
HTTP_OR_HTTPS = "http"
REVIEW_BULK = True
TIME_ZONE = 'America/Toronto'

# Selenium: which browser, and whether it is visible. Either can come from
# the environment for a one-off run instead:
#   SELENIUM_BROWSER=chromium pytest --run-selenium           # bash/zsh
#   $env:SELENIUM_BROWSER='chromium'; pytest --run-selenium   # PowerShell
# Selenium Manager resolves the driver itself; settings.py has the variables
# for pinning a specific binary.
#
# SELENIUM_BROWSER = 'chromium'   # 'firefox' is the default
# SELENIUM_HEADLESS = False       # watch it run; needs a real display

AUTHENTICATION_BACKENDS = ['qatrack.accounts.backends.QATrackAccountBackend']

# Customize any of the above settings as needed for your test environment
