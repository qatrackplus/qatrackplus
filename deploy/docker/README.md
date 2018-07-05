# QATrack+ with Docker

WARNING

This is a development version of QATrack+. It has not undergone sufficient testing.

## Prerequisites

### Docker and Docker-Compose

This installation method requires docker-compose and docker. Go to the following web address and follow all the relevant instructions to install docker and docker-compose on your system.

 * https://docs.docker.com/compose/install/
 * docker-compose can be as simple as `pip install docker-compose`

If you have issues using docker you may have to reboot your computer. If you are running linux it may also help to follow the post install instructions:

 * https://docs.docker.com/engine/installation/linux/linux-postinstall/

### Git

To easily retrieve files from bitbucket you will need git installed. Follow the relevant instructions at the following web address for your operating system:

 * https://www.atlassian.com/git/tutorials/install-git

## Docker QATrack+ (0.3.0-dev version) usage

### Downloading

    git clone https://bitbucket.org/SimonGBiggs/qatrackplus.git

    cd qatrackplus

    git checkout py34

    cd deploy/docker

### Installing

To run any docker-compose commands you need to be within the `qatrackplus/deploy/docker` directory. To build the server run the following:

    docker-compose build

To start the server once it has been built run:

    docker-compose up -d
    
This will start the server in such a way that it will automatically turn on when you boot your computer/server.

Go to http://localhost in browser to see the server.
If you get a `bad gateway` page please just refresh the page until the server has completed its start up procedure (approximately 10 seconds depending on your hardware). 
Default login is username admin, password admin.

### Customising your installation

All edits that normally would have gone within a custom `local_settings.py` file need to now go within `qatrackplus/deploy/docker/user_settings.py`.

There are also a range of environment variables that can be edited to suit your needs within `qatrackplus/deploy/docker/.env`.

If you wish to add extra python packages to your setup add them within `qatrackplus/deploy/docker/user_requirements.txt`. Follow the standard requirement file conventions explained at https://pip.pypa.io/en/stable/user_guide/.

After changing any files within qatrackplus you need to run the following to make the updates active.

    docker-compose stop
    docker-compose build
    docker-compose up -d

### Shutdown the server

To shutdown the server run:

    docker-compose stop

### Update server

To update the server from bitbucket run:

    docker-compose stop
    git pull

Once any files have changed in the qatrackplus directory you need to run the following:

    docker-compose build
    docker-compose up -d

### Backup management

Everytime `docker-compose up -d` is run a timestamped backup zip file of both the database and uploaded files is created. These backups are stored within `qatrackplus/deploy/docker/backup_management/backups`. To restore a backup zip file copy it to the restore directory found at `qatrackplus/deploy/docker/backup_management/restore`. The restoration will occur next time `docker-compose up -d` is called. After successful restoration all zip files within the restore directory are deleted.

This restore method will also successfully restore backup files created on a different machine. This way a fresh Docker QATrack+ installation on a new machine is able to start with your previously defined data.

### Delete all docker data

If for some reason you need it, the following command will delete all docker data from all docker projects:

    docker stop $(docker ps -a -q) && docker rm $(docker ps -a -q) && echo 'y' | docker volume prune
