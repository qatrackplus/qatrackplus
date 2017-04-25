# QATrack+ with Docker

WARNING

This is a development version of QATrack+. It has not undergone sufficient testing.

## Ubuntu Instructions

### Installing Docker

From https://docs.docker.com/engine/installation/linux/ubuntu/#install-docker

    sudo apt-get install \
        apt-transport-https \
        ca-certificates \
        curl \
        software-properties-common

    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    
    sudo add-apt-repository \
        "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) \
        stable"
        
    sudo apt-get update
    
    sudo apt-get install docker-ce
    
    sudo groupadd docker
    
    sudo usermod -aG docker $USER
    
Log out and log back in then run the following to see that everything is working:

    docker run hello-world
    
### Installing Docker Compose

From https://docs.docker.com/compose/install/

    curl -L https://github.com/docker/compose/releases/download/1.12.0/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
Optionally install command completion https://docs.docker.com/compose/completion/

Test docker-compose:

    docker-compose --version
    
### Downloading and installing Dockerised QATrack+ (0.3.0-dev version)

    git clone https://bitbucket.org/tohccmedphys/qatrackplus.git
    
    cd qatrackplus
    
    git checkout py34
    
    cd deploy/dockerised
    
    ./first-time.sh
    
### Running and viewing server

    ./start-server.sh
    
Go to http://localhost in browser.

### Update server after editing server files

    ./update-server-files.sh
    
### Wipe database and installation and start fresh

    ./delete-all-docker-containers.sh
    
### Backup database to file

Coming soon...

### Restore database from file

Coming soon...

### Update QATrack+ from a git

Coming soon...

### Dump database as CSV files for redundancy

Coming soon...

## Windows Instructions

Coming soon...

## OSX Instructions

Coming soon...
