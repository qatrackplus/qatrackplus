# Developer convenience targets - every one of them an alias for a poe task.
#
# **poe is the task runner; this file only forwards to it.** Nothing here
# carries any logic of its own, which is the point: when the Makefile and poe
# both held full implementations they drifted, and the drift was not cosmetic.
# `make-test-integration` stopped matching `make test-integration`,
# `docs-autobuild` served on a different port under each, and the two
# engine-swap implementations disagreed about whether to refuse a backup left
# by an interrupted run - so one of them destroyed the developer's settings.
# An alias cannot drift from what it calls.
#
# This file ships in every installation - QATrack+ is installed by `git clone` -
# so a target here can reach a production database. Nothing in it should be a
# shorter way to do something irreversible than doing it by hand. That now
# follows from the poe task it calls, so read the task.
#
# `args=` reaches pytest for the test and coverage targets, because those poe
# tasks are plain commands and poe appends to them:
#
#     make test args="-k test_foo"
#
# It does **not** reach the engine or integration targets. Those poe tasks are
# Python bodies that build their own argument list, so poe has nowhere to put
# extras and they are silently dropped - see the note above `test-engine` in
# poe_tasks/tests.toml. For a filtered run against one engine, swap
# qatrack/local_test_settings.py by hand and use `make test args="-k foo"`.
#
# `poe help` lists every task, including the ones with no Makefile target.

POE = uv run poe
ARGS = $(if $(args),-- $(args))


# Deliberately a written list rather than a grep over the file. A grep is how
# the two broken data-deleting targets came to be advertised alongside the
# working ones: `make help` presented everything, so it presented those too.
help:
	@echo "Every target here is an alias for the poe task of the same name."
	@echo "\`poe help\` lists the tasks that have no target."
	@echo
	@echo "Tests"
	@echo "  test              the suite; GUI/browser tests are skipped"
	@echo "  test_simple       the same thing - see the note in the Makefile"
	@echo "  test-sqlite       the suite against qatrack/local_test_settings.sqlite.py"
	@echo "  test-memory       the suite against qatrack/local_test_settings.memory.py"
	@echo "  test-postgres     the suite against qatrack/local_test_settings.postgres.py"
	@echo "  test-mysql        the suite against qatrack/local_test_settings.mysql.py"
	@echo "  test-mssql        the suite against qatrack/local_test_settings.mssql.py"
	@echo "  test-integration  provision a fresh sqlite database, then test against it"
	@echo "  cover             the suite with a coverage report"
	@echo "  cover-qatrack     coverage for the qatrack package only"
	@echo "  cover-module      coverage for one module: make cover-module module=qatrack/units"
	@echo "  cover-mo          coverage, skipping fully-covered files"
	@echo
	@echo "  For the GUI tests: uv run poe test-gui-firefox-headless (or -chromium-,"
	@echo "  or -visible to watch). Plain pytest skips them."
	@echo
	@echo "Docs"
	@echo "  docs              build the Sphinx docs"
	@echo "  docs-autobuild    serve the docs on :8008 and rebuild as you save"
	@echo
	@echo "Running"
	@echo "  run               the development server"
	@echo
	@echo "Data"
	@echo "  dumpdata          dump the database to a timestamped JSON fixture"
	@echo
	@echo "Release and deployment (read the poe task before running it)"
	@echo "  schema            regenerate the schema diagram - release task"
	@echo "  nginx.conf        install an nginx site config - sudo, Ubuntu only"
	@echo "  supervisor.conf   install supervisor configs - sudo, Ubuntu only"

cover:
	$(POE) cover $(ARGS)

cover-mo:
	$(POE) cover-mo $(ARGS)

cover-qatrack:
	$(POE) cover-qatrack $(ARGS)

# `module=` is the poe task's positional argument, so it is passed as one
# rather than through ARGS.
cover-module:
	$(POE) cover-module $(module)

test:
	$(POE) test $(ARGS)

# GUI (Selenium/browser) tests are skipped by default (see conftest.py), so
# this is identical to `test` - kept only so existing scripts and muscle
# memory using `make test_simple` keep working. Use `test` directly, or
# `uv run poe test-gui-firefox-headless` to run the GUI tests.
test_simple:
	$(POE) test $(ARGS)

# Run the suite against a specific engine's local_test_settings.py, without
# disturbing whatever you already have set up as your day-to-day one.
# Requires qatrack/local_test_settings.<engine>.py to already exist - these
# are gitignored and yours to create, starting from the matching
# deploy/dev/local_test_settings.<engine>.py template. The poe task backs up
# your current qatrack/local_test_settings.py, swaps the engine's file in for
# the run, and restores it afterwards; it refuses up front if a backup from a
# killed run is still there, rather than writing over your settings.
test-sqlite:
	$(POE) test-engine sqlite

test-memory:
	$(POE) test-engine memory

test-postgres:
	$(POE) test-engine postgres

test-mysql:
	$(POE) test-engine mysql

test-mssql:
	$(POE) test-engine mssql

# Provisions a database the way a real deployment would - migrate,
# createcachetable, collectstatic, createsuperuser - and then tests against
# that, rather than against a disposable test database. The poe task refuses
# unless your settings point at db/default.db, because otherwise it would
# migrate your real development database and leave a superuser/superuser
# account in it.
test-integration:
	$(POE) test-integration

dumpdata:
	$(POE) dumpdata

docs:
	$(POE) docs

docs-autobuild:
	$(POE) docs-autobuild

# The two targets below run sudo, write into /etc, and restart services. They
# are Ubuntu-specific and have never been exercised by CI or by either
# development machine. Read the poe task before running them on anything you
# care about. The dotted names are kept; the poe tasks use dashes.
nginx.conf:
	$(POE) nginx-conf

supervisor.conf:
	$(POE) supervisor-conf

# RELEASE TARGET. The schema diagram is distributed documentation, regenerated
# as part of a release check - not something an ordinary PR should update. The
# poe task renders to a temp file and only replaces the committed diagram if
# that worked: django-extensions falls back to pydotplus when pygraphviz is
# missing, and pydotplus fails by writing a zero-byte file and exiting 0, so
# the older form destroyed the committed 838KB diagram and reported success.
schema:
	$(POE) schema

run:
	$(POE) run

.PHONY: cover cover-mo cover-module cover-qatrack docs docs-autobuild \
	dumpdata help nginx.conf run schema supervisor.conf test \
	test-integration test-memory test-mssql test-mysql test-postgres \
	test-sqlite test_simple
