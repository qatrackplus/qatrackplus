#!/bin/bash

docker-compose build
docker-compose up -d
sleep 1
docker-compose run web bash -c 'python manage.py migrate && \
    echo "from django.contrib.auth.models import User; User.objects.create_superuser(\"admin\", \"myemail@example.com\", \"admin\")" | python manage.py shell && \
    python manage.py loaddata fixtures/defaults/*/* && \
    python manage.py collectstatic --noinput'
