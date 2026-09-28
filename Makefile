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
	@set -e; \
	if [ -f qatrack/local_test_settings.py.bak ]; then \
		echo "error: qatrack/local_test_settings.py.bak already exists."; \
		echo "An earlier run was interrupted before it could put your settings back."; \
		echo "Move it to qatrack/local_test_settings.py, or delete it, then try again."; \
		exit 1; \
	fi; \
	SWAPPED=0; \
	restore() { \
		[ "$$SWAPPED" = 1 ] || return 0; \
		if [ -f qatrack/local_test_settings.py.bak ]; then \
			mv -f qatrack/local_test_settings.py.bak qatrack/local_test_settings.py; \
		else \
			rm -f qatrack/local_test_settings.py; \
		fi; \
	}; \
	trap restore EXIT; \
	trap "exit 130" INT; \
	trap "exit 143" TERM; \
	if [ -f qatrack/local_test_settings.py ]; then \
		cp qatrack/local_test_settings.py qatrack/local_test_settings.py.bak; \
	fi; \
	cp qatrack/local_test_settings.$(ENGINE).py qatrack/local_test_settings.py; \
	SWAPPED=1; \
	uv run pytest ${args}

# Integration-level test: provisions a brand-new sqlite db exactly the way
# a fresh deployment would (migrate, createcachetable, collectstatic,
# createsuperuser), then runs the suite with --reuse-db (pytest-django's
# equivalent of Django's own --keepdb) directly against that same db,
# rather than a disposable one - so migrations, cache table creation,
# static collection, and the initial superuser are all exercised for real
# before the tests run, not just a fresh empty test db. Backs up any
# existing db/default.db and qatrack/local_test_settings.py first and
# restores both afterward regardless of whether the tests passed; the
#
# This target is the only thing that points the test database at
# db/default.db, and it does so by appending one line to its own copy of
# the settings file. The shipped template deliberately names a *separate*
# test database, because Django deletes a file-based test database before
# creating it and again at teardown - when the two names matched, a plain
# `pytest` destroyed the developer's populated db/default.db. The backup
# and restore below predate that discovery and stay as a second line of
# defence for this target, which really does want the two to be the same;
# freshly-provisioned db is kept, renamed with a `pytest_` prefix
# (overwriting the previous integration run), for inspection.
test-integration:
	@set -e; \
	mkdir -p db; \
	SWAPPED=0; \
	restore() { \
		[ "$$SWAPPED" = 1 ] || return 0; \
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
	trap "exit 130" INT; \
	trap "exit 143" TERM; \
	DBNAME=$$(uv run python -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qatrack.settings'); django.setup(); from django.conf import settings; print(settings.DATABASES['default']['NAME'])"); \
	if [ "$$DBNAME" != "db/default.db" ]; then \
		echo "error: this target provisions the database your settings point at, and that is"; \
		echo "         $$DBNAME"; \
		echo "not db/default.db. migrate, createcachetable, collectstatic and createsuperuser"; \
		echo "all read local_settings.py, not local_test_settings.py, so continuing would"; \
		echo "migrate that database and create a superuser/superuser account in it - while"; \
		echo "the tests ran somewhere else entirely."; \
		echo "Point local_settings.py at db/default.db before running this."; \
		exit 1; \
	fi; \
	if [ -f db/default.db.bak ] || [ -f qatrack/local_test_settings.py.bak ]; then \
		echo "error: a backup from an earlier run is still here:"; \
		[ -f db/default.db.bak ] && echo "  db/default.db.bak"; \
		[ -f qatrack/local_test_settings.py.bak ] && echo "  qatrack/local_test_settings.py.bak"; \
		echo "That run was interrupted before it could put them back. Restore or remove"; \
		echo "them first - continuing would overwrite them with throwaway copies."; \
		exit 1; \
	fi; \
	if [ -f db/default.db ]; then mv -f db/default.db db/default.db.bak; fi; \
	if [ -f qatrack/local_test_settings.py ]; then \
		cp qatrack/local_test_settings.py qatrack/local_test_settings.py.bak; \
	fi; \
	cp deploy/dev/local_test_settings.sqlite.py qatrack/local_test_settings.py; \
	SWAPPED=1; \
	printf "\n# test-integration only: test the database this target just\n# provisioned, rather than the template's separate test database.\nDATABASES['default']['TEST']['NAME'] = 'db/default.db'\n" \
		>> qatrack/local_test_settings.py; \
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

# Renders to a temp file and only replaces the committed diagram if it
# worked. The previous form wrote straight to the output path, and
# django-extensions falls back to pydotplus when pygraphviz is missing -
# pydotplus fails by writing a zero-byte file and exiting 0, so this target
# used to destroy the committed 838KB diagram and report success.
# --pygraphviz is explicit so a missing dependency fails loudly instead of
# silently taking the broken path; its wheels also bundle a current Graphviz,
# avoiding the "trouble in init_rank" bug in the 2.42 Ubuntu 24.04 ships.
# RELEASE TARGET - see the note on the poe `schema` task.
# WARNING: VERSION is 3.1.0 while the project is 4.0.x, so this overwrites the
# committed 3.1.0 diagram, which is tracked - not gitignored. Check
# `git status` afterwards and only keep the change if regenerating that
# release's diagram is what you meant to do.
schema:
	@out=docs/developer/images/qatrack_schema_$(VERSION).svg; \
	tmp=$$(mktemp -t qatrack-schema-XXXXXX.svg); \
	if uv run python ./manage.py graph_models -a -g --pygraphviz \
		-X Issue,IssueStatus,IssueType,IssuePriority,IssueTag \
		-o $$tmp && test -s $$tmp; then \
		mv -f $$tmp $$out; \
		echo "wrote $$out ($$(wc -c < $$out) bytes)"; \
	else \
		rm -f $$tmp; \
		echo "error: schema generation failed; $$out left untouched." >&2; \
		echo "Is pygraphviz installed? \`uv sync --dev\` should provide it." >&2; \
		exit 1; \
	fi

run:
	uv run python ./manage.py runserver

.PHONY: _test-engine cover cover-mo cover-module cover-qatrack docs \
	docs-autobuild dumpdata help nginx.conf run schema supervisor.conf test \
	test-integration test-memory test-mssql test-mysql test-postgres \
	test-sqlite test_simple
