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

test_simple:
	uv run pytest -m "not selenium" ${args}

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

.PHONY: cover cover-mo cover-module cover-qatrack docs docs-autobuild dumpdata \
	help nginx.conf run schema supervisor.conf test test_simple
