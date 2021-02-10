VERSION=3.1.0
DATETIME=$(shell date '+%Y-%m-%d_%H-%M-%S')


cover:
	py.test --reuse-db --cov-report term-missing --cov ./ ${args}

cover-mo:
	py.test --reuse-db --cov-report term-missing:skip-covered --cov ./ ${args}

test:
	py.test ${args}

test_simple:
	py.test -m "not selenium" ${args}

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
	sphinx-autobuild docs docs/_build/html -p 8009

qatrack_daemon.conf:
	sudo a2enmod headers
	sudo a2enmod proxy
	sudo sed 's/YOURUSERNAMEHERE/$(USER)/g' deploy/apache/apache24_daemon.conf > qatrack.conf
	sudo mv qatrack.conf /etc/apache2/sites-available/qatrack.conf
	sudo ln -sf /etc/apache2/sites-available/qatrack.conf /etc/apache2/sites-enabled/qatrack.conf
	sudo usermod -a -G $(USER) www-data
	sudo service apache2 restart

supervisor.conf:
	sudo sed 's/YOURUSERNAMEHERE/$(USER)/g' deploy/supervisor/django-q.conf > django-q.conf
	sudo mv django-q.conf /etc/supervisor/conf.d/
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
	qatrack_daemon.conf supervisor.conf schema run __cleardb__ mysql-ro-rights
