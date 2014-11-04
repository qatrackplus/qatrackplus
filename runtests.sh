#!/bin/bash

coverage erase &&
coverage run --branch --source='.' --omit='*migrations*' --omit='sqlserver_ado' manage.py test $@ &&
coverage report -m
