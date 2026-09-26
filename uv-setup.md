# QATrack+ Development Setup Guide

This guide will walk you through setting up a QATrack+ development environment from scratch, from cloning the repository to running tests.

> This is a quickstart. The canonical, fuller developer documentation is
> [`docs/developer/guide.rst`](docs/developer/guide.rst) (rendered as the
> *Developers Guide* in the Sphinx docs); [`CONTRIBUTING.md`](CONTRIBUTING.md)
> covers the contribution workflow and [`AGENTS.md`](AGENTS.md) the
> conventions expected of contributors and AI agents. If any of them
> disagree with this page, the developer guide wins — please fix the
> mismatch while you're there.

## Cloning your fork to your local system

Once you have created a fork of QATrack+ on GitHub, you will want to download your fork to your local system to work on.

```bash
git clone https://github.com/yourusername/qatrackplus.git
cd qatrackplus
```

## Setting up your development environment

QATrack+ now uses modern Python packaging with `pyproject.toml`, making setup much simpler. We recommend using uv for the fastest and most reliable dependency management.

### Using uv (Recommended - Fastest)

First, install uv globally:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/home/$USER/.local/bin:$PATH"
```

QATrack+ currently runs with the python 3.12 interpreter, as indicated in the `.python-version` file.
uv considers this file when running commands.

Create a virtual environment with Python 3.12 and install all dependencies:

```bash
cd /path/to/qatrackplus
uv sync --frozen

# This should create a python 3.12 virtual environment in the .venv directory with all necessary dependencies installed.

# --frozen is used to prevent uv sync from attempting to update the lock file, only using it as the source of truth.
```

Once you have the requirements installed, copy the debug `local_settings.py` file from the deploy subdirectory and then create your database:

```bash
cp deploy/dev/local_settings.dev.py qatrack/local_settings.py
cp deploy/dev/local_test_settings.sqlite.py qatrack/local_test_settings.py
mkdir -p db
python manage.py migrate
python manage.py createcachetable
python manage.py collectstatic --noinput
```

This will put a database called `default.db` in the `db` subdirectory.

## Running the development server

After the database is created, create a super user so you can log into QATrack+:

```bash
python manage.py createsuperuser
```

and then run the development server:

```bash
python manage.py runserver
```

Once the development server is running you should be able to visit http://127.0.0.1:8000 in your browser and log into QATrack+.

## Running tests

To verify your development environment is working correctly, you can run the test suite:

```bash
pytest
```

This runs everything except the GUI (Selenium/browser) tests, which are
skipped by default since they need a real Chromium or Firefox on the host.
For faster feedback during development, you can run specific test modules:

Run only admin tests:

```bash
python -m pytest qatrack/qa/tests/test_admin.py
```

Also run the GUI/Selenium tests (requires Chromium or Firefox installed):

```bash
python -m pytest --run-selenium
```

You should see output showing the tests running, with most tests passing.

## Troubleshooting

- **Missing dependencies**: If you encounter import errors, ensure you activated your virtual environment and installed the development dependencies with `uv sync --dev`.
- **Python version conflicts**: If you encounter compatibility issues, ensure you're using Python 3.12 with `uv python pin 3.12`. This creates the .python-version file.
- **Database issues**: Make sure you've copied the `local_settings.py` file and run migrations before starting the server.
- **Test failures**: the GUI (Selenium) tests are skipped unless you pass `--run-selenium`, so a plain `pytest` run should be green. If you do run them and they fail to start a browser, that is an environment problem (missing or sandboxed Chromium/Firefox), not an expected result — see the *Setting Up Selenium Browser Testing* section of the developer guide.

## Complete setup commands (copy-paste ready)

Complete uv setup:

```bash
git clone https://github.com/yourusername/qatrackplus.git
cd qatrackplus
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/home/$USER/.local/bin:$PATH"
uv python pin 3.12
uv sync --frozen
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
cp deploy/dev/local_settings.dev.py qatrack/local_settings.py
cp deploy/dev/local_test_settings.sqlite.py qatrack/local_test_settings.py
mkdir -p db
python manage.py migrate
python manage.py createcachetable
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py runserver
```

You're now ready to start developing QATrack+! 