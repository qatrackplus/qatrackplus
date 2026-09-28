# Developer convenience targets.
#
# This file ships in every installation - QATrack+ is installed by `git clone` -
# so a target here can reach a production database. Nothing in it should be a
# shorter way to do something irreversible than doing it by hand.

VERSION=3.1.0
DATETIME=$(shell date '+%Y-%m-%d_%H-%M-%S')


# Deliberately a written list rather than a grep over the file. A grep is how
# the two broken data-deleting targets came to be advertised alongside the
# working ones: `make help` presented everything, so it presented those too.
help:
	@echo "Tests"
	@echo "  test              the whole suite, including the GUI/browser tests"
	@echo "  test_simple       the suite without the GUI/browser tests"
	@echo "  cover             the suite with a coverage report"
	@echo "  cover-qatrack     coverage for the qatrack package only"
	@echo "  cover-module      coverage for one module: make cover-module module=qatrack/units"
	@echo "  cover-mo          coverage, skipping fully-covered files"
	@echo
	@echo "Docs"
	@echo "  docs              build the Sphinx docs"
	@echo "  docs-autobuild    serve the docs on :8009 and rebuild as you save"
	@echo
	@echo "Running"
	@echo "  run               the development server"
	@echo
	@echo "Data"
	@echo "  dumpdata          dump the database to a timestamped JSON fixture"
	@echo
	@echo "Release and deployment (read the target before running it)"
	@echo "  schema            regenerate the schema diagram - see the note in the Makefile"
	@echo "  nginx.conf        install an nginx site config - sudo, Ubuntu only"
	@echo "  supervisor.conf   install supervisor configs - sudo, Ubuntu only"

cover:
	uv run pytest --reuse-db --cov-report term-missing --cov ./ ${args}

cover-module:
	uv run pytest --cov-report term-missing --cov ./${module} ${module}

cover-mo:
	uv run pytest --reuse-db --cov-report term-missing:skip-covered --cov ./ ${args}

cover-qatrack:
	uv run pytest --reuse-db --cov-report term-missing --cov qatrack ${args}

test:
	uv run pytest ${args}

# GUI (Selenium/browser) tests are skipped by default now (see conftest.py),
# so this is identical to `test` - kept only so existing scripts and muscle
# memory using `make test_simple` keep working. Use `test` directly, or
# `uv run pytest --run-selenium` to also run the GUI tests.
test_simple:
	uv run pytest ${args}

# Run the suite against a specific engine's local_test_settings.py, without
# disturbing whatever you already have set up as your day-to-day one.
# Requires qatrack/local_test_settings.<engine>.py to already exist -
# these are gitignored and yours to create/customize (with real
# credentials for postgres/mysql/mssql), starting from the matching
# deploy/dev/local_test_settings.<engine>.py template. Backs up your
# current qatrack/local_test_settings.py (if any), swaps the requested
# engine's file in for the run, then restores it afterward regardless of
# whether the tests passed.
test-sqlite:
	@$(MAKE) --no-print-directory _test-engine ENGINE=sqlite

test-memory:
	@$(MAKE) --no-print-directory _test-engine ENGINE=memory

test-postgres:
	@$(MAKE) --no-print-directory _test-engine ENGINE=postgres

test-mysql:
	@$(MAKE) --no-print-directory _test-engine ENGINE=mysql

test-mssql:
	@$(MAKE) --no-print-directory _test-engine ENGINE=mssql

_test-engine:
	@test -f qatrack/local_test_settings.$(ENGINE).py || { \
		echo "error: qatrack/local_test_settings.$(ENGINE).py not found."; \
		echo "Create it first - see deploy/dev/local_test_settings.$(ENGINE).py for a starting template."; \
		exit 1; \
	}
	@if [ -f qatrack/local_test_settings.py ]; then \
		cp qatrack/local_test_settings.py qatrack/local_test_settings.py.bak; \
	fi
	cp qatrack/local_test_settings.$(ENGINE).py qatrack/local_test_settings.py
	@uv run pytest ${args}; \
	STATUS=$$?; \
	if [ -f qatrack/local_test_settings.py.bak ]; then \
		mv -f qatrack/local_test_settings.py.bak qatrack/local_test_settings.py; \
	else \
		rm -f qatrack/local_test_settings.py; \
	fi; \
	exit $$STATUS

# Integration-level test: provisions a brand-new sqlite db exactly the way
# a fresh deployment would (migrate, createcachetable, collectstatic,
# createsuperuser), then runs the suite with --reuse-db (pytest-django's
# equivalent of Django's own --keepdb) directly against that same db,
# rather than a disposable one - so migrations, cache table creation,
# static collection, and the initial superuser are all exercised for real
# before the tests run, not just a fresh empty test db. Backs up any
# existing db/default.db and qatrack/local_test_settings.py first and
# restores both afterward regardless of whether the tests passed; the
# freshly-provisioned db is kept, renamed with a `pytest_` prefix
# (overwriting the previous integration run), for inspection.
test-integration:
	@set -e; \
	mkdir -p db; \
	restore() { \
		if [ -f qatrack/local_test_settings.py.bak ]; then \
			mv -f qatrack/local_test_settings.py.bak qatrack/local_test_settings.py; \
		else \
			rm -f qatrack/local_test_settings.py; \
		fi; \
		if [ -f db/default.db.bak ]; then \
			mv -f db/default.db.bak db/default.db; \
		fi; \
	}; \
	trap restore EXIT; \
	if [ -f db/default.db ]; then mv -f db/default.db db/default.db.bak; fi; \
	if [ -f qatrack/local_test_settings.py ]; then \
		cp qatrack/local_test_settings.py qatrack/local_test_settings.py.bak; \
	fi; \
	cp deploy/dev/local_test_settings.sqlite.py qatrack/local_test_settings.py; \
	uv run python manage.py migrate; \
	uv run python manage.py createcachetable; \
	uv run python manage.py collectstatic --noinput; \
	DJANGO_SUPERUSER_USERNAME=superuser DJANGO_SUPERUSER_PASSWORD=superuser \
		DJANGO_SUPERUSER_EMAIL=superuser@example.com \
		uv run python manage.py createsuperuser --noinput; \
	set +e; uv run pytest --reuse-db ${args}; STATUS=$$?; set -e; \
	mv -f db/default.db db/pytest_default.db; \
	exit $$STATUS

dumpdata:
	uv run python manage.py dumpdata \
		-v1 --indent=2 --natural-foreign --natural-primary \
		--output qatrack-dump-$(DATETIME).json

docs:
	cd docs && uv run make html

docs-autobuild:
	uv run sphinx-autobuild docs docs/_build/html --port 8009

# The two targets below run sudo, write into /etc, and restart services. They
# are Ubuntu-specific and have never been exercised by CI or by either
# development machine. Read them before running them on anything you care about.
nginx.conf:
	sudo sed 's/YOURUSERNAMEHERE/$(USER)/g' deploy/nginx/qatrack.conf > qatrack.conf
	sudo mv qatrack.conf /etc/nginx/sites-available/qatrack.conf
	sudo ln -sf /etc/nginx/sites-available/qatrack.conf /etc/nginx/sites-enabled/qatrack.conf
	sudo usermod -a -G $(USER) www-data
	sudo service nginx restart

supervisor.conf:
	sudo sed 's/YOURUSERNAMEHERE/$(USER)/g' deploy/supervisor/django-q2.conf > django-q2.conf
	sudo sed 's/YOURUSERNAMEHERE/$(USER)/g' deploy/supervisor/gunicorn.conf > gunicorn.conf
	sudo mv django-q2.conf /etc/supervisor/conf.d/
	sudo mv gunicorn.conf /etc/supervisor/conf.d/
	sudo supervisorctl reread
	sudo supervisorctl update

# WARNING: VERSION is 3.1.0 while the project is 4.0.0, so this overwrites the
# published 3.1.0 diagram. Check `git status` afterwards.
schema:
	uv run python ./manage.py graph_models -a -g \
		-X Issue,IssueStatus,IssueType,IssuePriority,IssueTag \
		-o docs/developer/images/qatrack_schema_$(VERSION).svg

run:
	uv run python ./manage.py runserver

.PHONY: _test-engine cover cover-mo cover-module cover-qatrack docs \
	docs-autobuild dumpdata help nginx.conf run schema supervisor.conf test \
	test-integration test-memory test-mssql test-mysql test-postgres \
	test-sqlite test_simple
