import os
import re

from setuptools import find_packages, setup

root = os.path.dirname(__file__)

settingsf = open(os.path.join(root, 'qatrack', 'settings.py'), 'r')

__version__ = re.findall("""VERSION\s+=\s+['"]+(.*)['"]""", settingsf.read())[0]

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
        "git+https://github.com/django/django-formtools.git@bb97a8abd374c50991c0a9ce144f17e7322a0c48#egg=django-formtools",
        "git+https://github.com/randlet/django-genericdropdown.git@2117e449977ba9387941eb94e37d82208e53c1ad#egg=django-genericdropdown",
        "git+https://github.com/randlet/django-listable.git@efff32a4ceaa795d5b1a32dc75decacef3de90e8#egg=django_listable",
    ],
    build_requires=[
        "numpy<=1.15.2",
    ],
    setup_requires=[
        "numpy<=1.15.2",
    ],
    install_requires=[
        "django-formtools",
        "django-genericdropdown",
        "django_listable",
        "Django>=1.11,<2",
        "PyVirtualDisplay>=0.2,<0.3",
        "coreapi>=2.3,<2.4",
        "coverage>=4.5,<5",
        "django-admin-views>=0.8.0,<0.9",
        "django-braces>=1.13.0,<1.14",
        "django-contrib-comments>=1.8.0<1.9",
        "django-coverage>=1.2,<1.3",
        "django-crispy-forms>=1.6.0,<1.7",
        "django-debug-toolbar>=1.8,<1.9",
        "django-dynamic-raw-id==2.4",
        "django-extensions>=1.7,<1.8",
        "django-filter>=1.1.0,<1.2",
        "django-form-utils>=1.0,<1.1",
        "django-registration>=2.1,<2.2",
        "djangorestframework>=3.7.0,<3.8",
        "djangorestframework-filters>=0.10.2post0,<0.11",
        "django-tastypie>=0.13,<0.14",
        "django-widget-tweaks>=1.4,<1.5",
        "freezegun>=0.3,<0.4",
        "markdown>=2.6,<2.7",
        "matplotlib>=2.2,<2.3",
        "numpy<=1.15.2",
        "pandas>=0.22.0,<0.25",
        "pep8>=1.7.0",
        "pydicom>=1.1,<1.2",
        "pylinac>=2.1,<2.3",
        "pynliner>=0.8.0,<0.9",
        "pytest-cov>=2.5.1",
        "pytest-django>=3.1.2",
        "pytest-sugar>=0.9.1",
        "pytest>=3.5.0",
        "python-dateutil>=2.6.1,<2.7",
        "pytz>=2018.4",
        "reportlab>=3.5,<3.6",
        "requests>=2.18,<2.19",
        "scipy<=1.1.0",
        "selenium>=3.11.0,<3.12",
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
