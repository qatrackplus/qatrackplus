# QATrack+ with Docker

WARNING

This is a development version of QATrack+. It has not undergone sufficient testing.

## Prerequisites

This has been tested with Ubuntu 18.04

### Docker and Docker-Compose

Go to the following web address and follow all the relevant instructions to install docker-ce and docker-compose on your system.

* docker-ce -- <https://docs.docker.com/install/>
  * On Ubuntu 18.04 this can be achieved with `sudo snap install docker`
* docker-compose -- `pip install docker-compose`

If you have issues using docker you may have to reboot your computer. If you are running linux it may also help to follow the post install instructions:

* <https://docs.docker.com/engine/installation/linux/linux-postinstall/>

Before continuing please verify that you can run `docker run hello-world` in a terminal.

### Git

To retrieve files from bitbucket you will need git installed. Follow the relevant instructions at the following web address for your operating system:

* <https://www.atlassian.com/git/tutorials/install-git>

## Docker QATrack+ (0.3.0-dev version) usage

### Downloading

    git clone https://bitbucket.org/SimonGBiggs/qatrackplus.git
    cd qatrackplus
    git checkout py34
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

Default login is username admin, password admin. You should change this through
the admin interface once you have first logged in.

### Accessing the Django shell

If you need to access the Django shell run the following in another terminal:

```bash
docker exec -ti docker_qatrack-django_1 /bin/bash
source deploy/docker/user-data/python-virtualenv/bin/activate
python manage.py shell
```

This requires that the containers are already running.

### Making QATrack+ start on boot

```bash
docker-compose up -d
```

This will start the server in such a way that it will automatically turn on when you boot your computer/server.

### Changing from port 80 to a different port

The first number of the `ports` item within `docker-compose.yml` can be changed
to use a port that is different to port 80. For example, if `80:80` was changed
to `8080:80` then you would need to type <http://localhost:8080> within your
browser to see QATrack+.

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

If for some reason you need it, the following command will delete all docker data from all docker projects (WARNING, IRREVERSABLE):

```bash
docker stop $(docker ps -a -q) && docker rm $(docker ps -a -q)
```

And this will delete all of the cache:

```bash
echo 'y' | docker volume prune
```
