VERSION=0.3.0

cover :
	py.test --reuse-db --cov-report term-missing --cov ./ ${args}

test:
	py.test ${args}

test_simple:
	py.test -m "not selenium" ${args}

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
	sphinx-autobuild docs docs/_build/html -p 8008

qatrack_daemon.conf:
	sudo sed 's/YOURUSERNAMEHERE/$(USER)/g' deploy/apache24_daemon.conf > qatrack.conf
	sudo mv qatrack.conf /etc/apache2/sites-available/qatrack.conf
	sudo ln -sf /etc/apache2/sites-available/qatrack.conf /etc/apache2/sites-enabled/qatrack.conf
	sudo usermod -a -G $(USER) www-data
	sudo service apache2 restart

schema:
	python ./manage.py graph_models -a -g \
		-X Issue,IssueStatus,IssueType,IssuePriority,IssueTag \
		-o docs/developer/images/qatrack_schema_$(VERSION).svg

run:
	python ./manage.py runserver

.PHONY: test test_simple test_broker yapf flake8 help autobuild docs qatrack_daemon.conf schema run
