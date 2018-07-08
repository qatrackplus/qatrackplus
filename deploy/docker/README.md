# QATrack+ with Docker

WARNING

This is a development version of QATrack+. It has not undergone sufficient testing.

## Prerequisites

## Ubuntu vs Windows

This has been tested with Ubuntu 18.04. The method explained here uses docker
local volume mounting which isn't as consistent between Linux and Windows
machines. It has the benefit of being simpler to understand what is going on
and having all of the qatrack live data be saved within this repository.

Of course a second, less simple and less transparent method can be implemented
for Windows support if the demand is there. But arguably it might be better to
install [ubuntu server](https://www.ubuntu.com/download/server) within
[virtual box](https://www.virtualbox.org/) port forward [port 80](https://www.howtogeek.com/122641/how-to-forward-ports-to-a-virtual-machine-and-use-it-as-a-server/)
and then follow these instructions as is.

### Docker and Docker-Compose

Go to the following web address and follow all the relevant instructions to install docker-ce and docker-compose on your system.

* docker-ce -- `sudo snap install docker` or see <https://docs.docker.com/install/> for other install methods
* docker-compose -- `pip install docker-compose`

You will also need to implement the following to be able to run docker without
sudo:

* <https://docs.docker.com/engine/installation/linux/linux-postinstall/>

After completing these post install tasks please reset your computer.

Before continuing please verify that you can run `docker run hello-world` in a
terminal.

### Git

To retrieve files from bitbucket you will need git installed by running the
following:

```bash
sudo apt install git
```

## Docker QATrack+ (0.3.0-dev version) usage

### Downloading

    git clone https://bitbucket.org/SimonGBiggs/qatrackplus.git
    cd qatrackplus
    git checkout simon-docker
    cd deploy/docker

### Installing

To run any docker-compose commands you need to be within the
`qatrackplus/deploy/docker` directory. To build and start the server run the
following:

    docker-compose build
    docker-compose up

On initial run this will take quite some time to load.

Wait until you see something like the following within your terminal:

```bash
qatrack-django_1    | [2018-07-07 15:31:44 +0000] [509] [INFO] Starting gunicorn 19.3.0
qatrack-django_1    | [2018-07-07 15:31:44 +0000] [509] [INFO] Listening at: http://0.0.0.0:8000 (509)
qatrack-django_1    | [2018-07-07 15:31:44 +0000] [509] [INFO] Using worker: sync
qatrack-django_1    | [2018-07-07 15:31:44 +0000] [512] [INFO] Booting worker with pid: 512
qatrack-django_1    | [2018-07-07 15:31:44 +0000] [514] [INFO] Booting worker with pid: 514
```

Once the `Listening at: http://0.0.0.0:8000` line is visible go to
<http://localhost> in your computer's browser to see the server.

Default login is username `admin`, password `admin`. You should change this
through the QATrack+ admin interface once you have first logged in.

### Accessing the Django shell

If you need to access the Django shell run the following in another terminal:

```bash
docker exec -ti docker_qatrack-django_1 /bin/bash
source deploy/docker/user-data/python-virtualenv/bin/activate
python manage.py shell
```

This requires that the containers are already running.

### Making QATrack+ start on boot and run in the background

```bash
docker-compose up -d
```

This will start the server in such a way that it will automatically turn on when you boot your computer/server.

### Changing from port 80 to a different port

The first number of the `ports` item within `docker-compose.yml` can be changed
to use a port that is different to port 80. For example, if `80:80` was changed
to `8080:80` then you would need to type <http://localhost:8080> within your
browser to see QATrack+. After editing `docker-compose.yml` you need to rerun
`docker-compose up`.

### Shutdown the server

To shutdown the server run:

    docker-compose stop

### Update server

To update the server from bitbucket run:

    docker-compose stop
    git pull

Once any files have changed in the qatrackplus directory you need to run the following:

    docker-compose build
    docker-compose up

### Backup management

Everytime `docker-compose up` is run a timestamped backup zip file of both the database and uploaded files is created. These backups are stored within `qatrackplus/deploy/docker/user-data/backup-management/backups`. To restore a backup zip file copy it to the restore directory found at `qatrackplus/deploy/docker/user-data/backup-management/restore`. The restoration will occur next time `docker-compose up` is called. After successful restoration the zip file within the restore directory is deleted.

This restore method will also successfully restore backup files created on a different machine.
However it will only successfully restore a like for like QATrack+ version.
This cannot be used when upgrading between versions.

### Delete all docker data

If for some reason you need it, the following command will delete all docker data from all docker projects (WARNING, IRREVERSABLE):

```bash
docker stop $(docker ps -a -q) && docker rm $(docker ps -a -q)
```

And this will delete all of the cache:

```bash
echo 'y' | docker volume prune
```
