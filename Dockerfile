FROM python:3.6-onbuild

RUN mv /usr/src/app/deploy/docker/docker_settings.py /usr/src/app/qatrack/local_settings.py
