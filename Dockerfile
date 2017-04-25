FROM python:3.4-onbuild

RUN mv /usr/src/app/qatrack/docker_settings.py /usr/src/app/qatrack/local_settings.py
