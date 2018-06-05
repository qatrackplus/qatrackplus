test:
	py.test

docs:
	cd docs && make html

autobuild:
	sphinx-autobuild docs docs/_build/html

.PHONY: help autobuild test docs
