#!/bin/bash
coverage erase
coverage run --source='.' manage.py test $@
coverage report
