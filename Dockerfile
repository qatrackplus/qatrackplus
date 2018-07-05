FROM python:3.6

RUN mkdir -p /usr/src/install
WORKDIR /usr/src/install

COPY requirements.txt /usr/src/install/
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /usr/src/qatrackplus