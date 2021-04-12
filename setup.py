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
        "git+https://github.com/randlet/django-genericdropdown.git@473ff52610af659f7d2a3616a6e3322e21673b4d#egg=django_genericdropdown"  # noqa: E501
        "git+https://github.com/randlet/django-recurrence.git@b3a73e8e03952107e58382922fec37aead31fd6f#egg=django-recurrence"  # noqa: E501
        "git+https://github.com/randlet/django-sql-explorer.git@12802fe83f9c45fd0bbe9610cb442dcfc5666d44#egg=django-sql-explorer"  # noqa: E501
    ],
    build_requires=[
        "numpy<1.21",
    ],
    setup_requires=[
        "numpy<1.21",
    ],
    install_requires=[
        "django-genericdropdown",
        "django-recurrence",
        "django-sql-explorer",
        "black>=20.8b1,<20.9",
        "Django>=2.2.18,<3",
        "django-q>=1.3.4,<1.4",
        "PyVirtualDisplay>=2.0,<2.1",
        "beautifulsoup4>=4.9.3,<5",
        "concurrent-log-handler>=0.9.19,<0.10",
        "coreapi>=2.3.3,2.4",
        "coverage>=5.4,<5.5",
        "django-admin-views>=0.8.0,<0.9",
        "django-auth-adfs>=1.6.0,<1.7",
        "django-braces>=1.13.0,<1.14",
        "django-contrib-comments>=1.8.0,<1.9",
        "django-coverage>=1.2.4,<1.3",
        "django-crispy-forms>=1.6.0,<1.7",
        "django-debug-toolbar>=2.0,<2.1",
        "django-dynamic-raw-id>=2.8,<2.9",
        "django-extensions>=3.1.0,<3.2",
        "django-filter>=2.1.0,<2.2",
        "django-form-utils>=1.0.3,<1.1",
        "django-formtools>=2.1,<2.2",
        "django-listable>=0.5.0,<0.6",
        "django-mptt>=0.10.0,<0.11",
        "django-mptt-admin>=0.7.2,<0.8",
        "django-picklefield>=2.0,<2.1",
        "django-registration>=3.1.1,<3.2",
        "djangorestframework>=3.12.2,<3.13",
        "djangorestframework-filters>=1.0.0_dev0,<1.1",
        "django-widget-tweaks>=1.4.1,<1.5",
        "freezegun>=0.3.15,<0.4",
        "html5lib>=1.1,<1.2",
        "markdown>=2.6.11,<2.7",
        "matplotlib>=2.2.2,<2.3",
        "numpy>=1.20.0,<1.21",
        "pandas>=1.1,<1.2",
        "pep8>=1.7.0,<1.8",
        "pydicom>=2.1.2,<2.2",
        "pylinac-qatrackplus>=2.3.1.5",
        "pynliner>=0.8.0,<0.9",
        "pytest-cov>=2.11.1,<2.12",
        "pytest-django>=4.1.0,<4.2",
        "pytest-sugar>=0.9.4,<0.10",
        "pytest>=6.2.2,<6.3",
        "python-dateutil>=2.8.1,<2.9",
        "pytz>=2021.1",
        "reportlab>=3.5.59,<3.6",
        "requests>=2.21.0,<2.22",
        "scipy<=1.5.4,<1.6",
        "selenium>=3.141.0,<3.142",
        "XlsxWriter>=1.3.7,<1.4",
    ],
    license='MIT',
    test_suite='tests',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Django 1.11",
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
