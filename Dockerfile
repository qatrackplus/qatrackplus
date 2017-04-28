FROM python:3.4-onbuild

RUN mv /usr/src/app/deploy/dockerised/local_settings.py /usr/src/app/qatrack/local_settings.py
