# QATrack+ with Docker

WARNING

This is a development version of QATrack+. It has not undergone sufficient testing.

## Installation instructions

This installation method requires docker-compose and docker. Go to the following web adress and follow all the relevant instructions to install docker and docker-compose on your system.

 * https://docs.docker.com/compose/install/

## Dockerised QATrack+ (0.3.0-dev version) usage

### Downloading

    git clone https://bitbucket.org/tohccmedphys/qatrackplus.git

    cd qatrackplus

    git checkout py34

    cd deploy/dockerised

### Installing

To run any docker-compose commands you need to be within the `qatrackplus/deploy/dockerised` directory. To build the server run the following:

    docker-compose build

To start the server once it has been built run:

    docker-compose up -d

The first time this is run the server needs about 5 seconds to initialise. Go to http://localhost in browser to see the server. Default login is username admin, password admin.

### Shutdown the server

To shutdown the server run:

    docker-compose stop

### Update server

To update the server from bitbucket run:

    git pull

Once any files have changed in the qatrackplus directory you need to run the following:

    docker-compose stop
    docker-compose build
    docker-compose up -d

### Backup database to file

Coming soon...

### Restore database from file

Coming soon...

### Dump database as CSV files for redundancy

Coming soon...
