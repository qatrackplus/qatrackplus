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
        "beautifulsoup4==4.14.3",
        "black==26.5.1",
        "click==8.4.1",
        "concurrent-log-handler==0.9.29",
        "coreapi==2.3.3",
        "coverage==7.14.0",
        "Django==6.0.5",
        "django-admin-views==1.0.3",
        "django-auth-adfs==1.16.0",
        "django-braces==1.17.0",
        "django-contrib-comments==2.2.0",
        "django-coverage==1.2.4",
        "django-crispy-forms==2.6",
        "django-debug-toolbar==6.3.0",
        "django-dynamic-raw-id==4.4",
        "django-extensions==4.1",
        "django-filter==25.2",
        "django-formtools==2.6.1",  # might need amending and putting on github
        "django-listable==0.9.4",  # might need amending and putting on github
        "django-mptt==0.18.0",
        "django-mptt-admin==2.9.0",
        "django-picklefield==3.4.0",
        "django-q2==1.10.0",
        "django-recurrence==1.14",  # might need amending and putting on github
        "django-registration==5.2.1",
        "django-sql-explorer==5.3",  # might need amending and putting on github
        "django-widget-tweaks==1.5.1",
        "djangorestframework==3.17.1",  # might need amending and putting on github
        "freezegun==1.5.5",
        "html5lib==1.1",
        "Markdown==3.10.2",
        "matplotlib==3.10.9",
        "numpy==2.4.6",
        "openpyxl==3.1.5",
        "pandas==3.0.3",
        "pep8==1.7.1",
        "pillow==12.2.0",
        "pydicom==2.4.5",
        "pylinac==3.44.0",
        "pynliner==0.8.0",
        "pytest==9.0.3",
        "pytest-cov==7.1.0",
        "pytest-django==4.12.0",
        "pytest-sugar==1.1.1",
        "python-dateutil==2.9.0.post0",
        "PyVirtualDisplay==3.0",
        "reportlab==4.5.1",
        "requests==2.34.2",
        "scipy==1.17.1",
        "selenium==4.44.0",
        "standard-imghdr==3.13.0",
        "tzdata==2026.2",
        "xlrd==2.0.2",
        "xlsxwriter==3.2.9",
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
