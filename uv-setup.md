# QATrack+ Development Setup Guide

This guide will walk you through setting up a QATrack+ development environment from scratch, from cloning the repository to running tests.

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
mkdir db
python manage.py migrate
python manage.py createcachetable
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
py.test
```

This will run all tests. For faster feedback during development, you can run specific test modules:

Run only admin tests:

```bash
python -m pytest qatrack/qa/tests/test_admin.py
```

Run only non-selenium tests (faster):

```bash
python -m pytest -m "not selenium"
```

You should see output showing the tests running, with most tests passing. Some selenium-based browser tests may fail depending on your environment, but the core functionality tests should all pass.

## Troubleshooting

- **Missing dependencies**: If you encounter import errors, ensure you activated your virtual environment and installed the development dependencies with `uv sync --group dev`.
- **Python version conflicts**: If you encounter compatibility issues, ensure you're using Python 3.12 with `uv python pin 3.12`. This creates the .python-version file.
- **Database issues**: Make sure you've copied the `local_settings.py` file and run migrations before starting the server.
- **Test failures**: Some selenium browser tests may fail due to browser/environment issues. This is normal and doesn't affect core functionality.

## Complete setup commands (copy-paste ready)

Complete uv setup:

```bash
git clone https://github.com/yourusername/qatrackplus.git
cd qatrackplus
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/home/$USER/.local/bin:$PATH"
uv python pin 3.12
uv sync --frozen
source .venv/bin/activate
cp deploy/dev/local_settings.dev.py qatrack/local_settings.py
mkdir db
python manage.py migrate
python manage.py createcachetable
python manage.py createsuperuser
python manage.py runserver
```

You're now ready to start developing QATrack+! 