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
	qatrack_daemon.conf supervisor.conf schema run __cleardb__ mysql-ro-rights
