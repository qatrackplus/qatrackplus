VERSION=3.1.0
DATETIME=$(shell date '+%Y-%m-%d_%H-%M-%S')


cover:
	py.test --reuse-db --cov-report term-missing --cov ./ ${args}

cover-module:
	py.test --cov-report term-missing --cov ./${module} ${module}

cover-mo:
	py.test --reuse-db --cov-report term-missing:skip-covered --cov ./ ${args}

cover-qatrack:
	py.test --reuse-db --cov-report term-missing --cov qatrack ${args}

test:
	py.test ${args}

# GUI (Selenium/browser) tests are skipped by default now (see conftest.py),
# so this is identical to `test` - kept only so existing scripts and muscle
# memory using `make test_simple` keep working. Use `test` directly, or
# `py.test --run-selenium` to also run the GUI tests.
test_simple:
	py.test ${args}

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
	@mkdir -p db
	@if [ -f db/default.db ]; then \
		mv -f db/default.db db/default.db.bak; \
	fi
	@if [ -f qatrack/local_test_settings.py ]; then \
		cp qatrack/local_test_settings.py qatrack/local_test_settings.py.bak; \
	fi
	cp deploy/dev/local_test_settings.sqlite.py qatrack/local_test_settings.py
	uv run python manage.py migrate
	uv run python manage.py createcachetable
	uv run python manage.py collectstatic --noinput
	DJANGO_SUPERUSER_USERNAME=superuser DJANGO_SUPERUSER_PASSWORD=superuser DJANGO_SUPERUSER_EMAIL=superuser@example.com \
		uv run python manage.py createsuperuser --noinput
	@uv run pytest --reuse-db ${args}; \
	STATUS=$$?; \
	mv -f db/default.db db/pytest_default.db; \
	if [ -f qatrack/local_test_settings.py.bak ]; then \
		mv -f qatrack/local_test_settings.py.bak qatrack/local_test_settings.py; \
	else \
		rm -f qatrack/local_test_settings.py; \
	fi; \
	if [ -f db/default.db.bak ]; then \
		mv -f db/default.db.bak db/default.db; \
	fi; \
	exit $$STATUS

dumpdata:
	python manage.py dumpdata \
		-v1 --indent=2 --natural-foreign --natural-primary \
		--output qatrack-dump-$(DATETIME).json

clearct:
	python manage.py shell -c "from qatrack.qa.models import *; [m.objects.all().delete() for m in [ContentType, Tolerance, User]]"

flushdb:
	python manage.py sqlflush | python manage.py dbshell

yapf:
	yapf --verbose --in-place --recursive --parallel \
		-e*fixtures* -e*migration* -e*.git* -e*tmp* -e*deploy* \
		-e*media* -e deploy  -e env -e*templates* -e*backups* -e*ipynb* -e*static* \
		-e*logs* -e*cache* -e*init.d* -e*emails* -e*postgres* -e*uploads* \
		.

flake8:
	flake8 .

docs:
	cd docs && make html

docs-autobuild:
	sphinx-autobuild docs docs/_build/html --port 8009

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

schema:
	python ./manage.py graph_models -a -g \
		-X Issue,IssueStatus,IssueType,IssuePriority,IssueTag \
		-o docs/developer/images/qatrack_schema_$(VERSION).svg

run:
	python ./manage.py runserver

__cleardb__:
	python manage.py shell -c "from qatrack.qa.models import *; TestListInstance.objects.all().delete(); UnitTestCollection.objects.all().delete(); ContentType.objects.all().delete()"

.PHONY: test test_simple yapf flake8 help docs-autobuild docs \
	qatrack_daemon.conf supervisor.conf schema run __cleardb__ mysql-ro-rights \
	_test-engine test-integration test-memory test-mssql test-mysql \
	test-postgres test-sqlite
