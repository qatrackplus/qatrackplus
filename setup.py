import os
import re

from setuptools import find_packages, setup

root = os.path.dirname(__file__)

settingsf = open(os.path.join(root, 'qatrack', 'settings.py'), 'r')

__version__ = re.findall(r"""VERSION\s+=\s+['"]+(.*)['"]""", settingsf.read())[0]

setup(
    name='qatrackplus',
    version=__version__,
    packages=find_packages(exclude=["local_settings", "local_test_settings"]),
    include_package_data=True,
    description=(
        "QATrack+ is an open source application for managing QC data in radiotherapy and diagnostic imaging clinics"
    ),
    long_description=open('README.md').read(),
    zip_safe=False,
    url='http://qatrackplus.com/',
    keywords="QATrack+ medical physics TG142 quality assurance linac CT MRI radiotherapy diagnostic imaging",
    author='QATrack+ contributors',
    author_email='randy@multileaf.ca',
    dependency_links=[
        "git+https://github.com/maan8005/Django-genericdropdown.git#egg=django-genericdropdown"  # noqa: E501
        "git+https://github.com/maan8005/django-rest-framework-filters.git#egg=djangorestframework-filters"  # noqa: E501
        "git+https://github.com/maan8005/django-form-utils.gitt#egg=django-form-utils"  # noqa: E501
    ],
    build_requires=[
        "numpy",
    ],
    setup_requires=[
        "numpy",
    ],
    install_requires=[
        "django-genericdropdown",
        "django-recurrence",
        "django-sql-explorer",
        "black",
        "Django",
        "django-q2",
        "PyVirtualDisplay",
        "beautifulsoup4",
        "concurrent-log-handler",
        "coreapi",
        "coverage",
        "django-admin-views",
        "django-auth-adfs",
        "django-braces",
        "django-contrib-comments",
        "django-coverage",
        "django-crispy-forms",
        "django-debug-toolbar",
        "django-dynamic-raw-id",
        "django-extensions",
        "django-filter",
        "django-form-utils",
        "django-formtools",
        "django-listable",
        "django-mptt",
        "django-mptt-admin",
        "django-picklefield",
        "django-registration",
        "djangorestframework",
        "djangorestframework-filters",
        "django-widget-tweaks",
        "freezegun",
        "html5lib",
        "markdown",
        "matplotlib",
        "numpy",
        "pandas",
        "pep8",
        "pydicom",
        "pylinac",
        "pynliner",
        "pytest-cov",
        "pytest-django",
        "pytest-sugar",
        "pytest",
        "python-dateutil",
        "reportlab",
        "requests",
        "scipy",
        "selenium",
        "tzdata",
        "XlsxWriter",
    ],
    license='MIT',
    test_suite='tests',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Django ",
        "Intended Audience :: Developers",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python",
        "Programming Language :: JavaScript",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Software Development :: Version Control :: Git",
    ]
)
