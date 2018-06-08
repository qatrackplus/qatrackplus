cover :
	py.test --reuse-db --cov-report term-missing --cov ./ ${args}

test:
	py.test ${args}

test_simple:
	py.test --reuse-db -m "not selenium" ${args}

yapf:
	yapf --verbose --in-place --recursive --parallel \
		-e*fixtures* -e*migration* -e*.git* -e*tmp* -e*deploy* \
		-e*media* -e*pgpool* -e*templates* -e*backups* -e*ipynb* -e*static* \
		-e*logs* -e*cache* -e*init.d* -e*emails* -e*postgres* -e*uploads* \
		.

flake8:
	flake8 .

.PHONY: test test_simple test_broker yapf flake8
