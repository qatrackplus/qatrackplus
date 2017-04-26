#!/bin/bash

docker-compose build 
docker-compose up -d 
docker-compose run web bash -c 'python manage.py collectstatic --noinput'
