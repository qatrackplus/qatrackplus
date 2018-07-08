FROM python:3.6

RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ stretch-pgdg main' > /etc/apt/sources.list.d/pgdg.list
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
RUN apt-get update
RUN apt-get install -y cron postgresql-client-10

RUN touch /root/.is_inside_docker

RUN pip install virtualenv

WORKDIR /usr/src/qatrackplus