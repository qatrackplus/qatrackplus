# QATrack+ with Docker

WARNING

This is a development version of QATrack+ and a developmental install method.
It is undergoing iterative development, is not currently stable, and has not
been sufficiently tested.

## Prerequisites by OS

This has been tested under two setups, Ubuntu 18.04, or Windows 10.
Depending on which system you are using there are different ways to install
the required dependencies. Follow the section that applies to your specific
machine.

### Windows 10 Professional or Enterprise with Hyper-V

The aim of this setup is to have a complete installation of QATrack+ on a
Windows 10 Professional or Enterprise machine with the backups being
scheduled to be periodically copied to a OneDrive directory.

#### Ensure Virtualisation is enabled

This setup uses Hyper-V. To use Hyper-V you need Windows 10 Professional or
Enterprise with virtualisation enabled. To verify that virtualisation
is enabled open the task manager, select `More details`, click on the `Performance`
tab and verify that in the bottom right it states `Virtualisation: Enabled` as
in the following screenshot:

![Virtualisation enabled](https://docs.docker.com/docker-for-windows/images/virtualization-enabled.png)

If this says disabled then this will need to be enabled within your machines
BIOS before continuing.

See <https://docs.docker.com/docker-for-windows/troubleshoot/#virtualization>
for further troubleshooting if required.

#### Chocolatey

To simplify this guide all installation will be done via the chocolatey package
manager. To install chocoletey run the following in a command prompt with
administrative privileges.

!(Administrator Privileges)[https://www.howtogeek.com/wp-content/uploads/2016/12/ximg_585a0e5711605.png.pagespeed.gp+jp+jw+pj+ws+js+rj+rp+rw+ri+cp+md.ic.3-azGXR2bH.png]

```cmd
@"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
```

For more information on chocolatey see <https://chocolatey.org/>

#### Docker for Windows, and Git

To install Docker for Windows, Docker Compose and Git run the following
within and administrative command prompt:

```cmd
choco install git docker-for-windows -y
```

Reboot your machine.

Run the newly created `Docker for Windows` icon that has appeared
on the desktop. If prompted to approve the request to enable Hyper-V. Thise will
once again reboot your computer.

You should not need to click this icon again.

After multiple reboots Docker will begin downloading and setting up its virtual machine.
This will take some time and you may notice the PC running slow while it is working
on this.

Specifically you are waiting until the following popup is displayed:

![Docker Welcome](https://docs.docker.com/docker-for-windows/images/docker-app-welcome.png)

On my machine this docker initialisation process took a little over 15 minutes.

To test that docker is working as expected run the following in a command prompt:

```cmd
docker run hello-world
```

#### Enable shared drives within Docker for Windows

Right click on the whale in the notification panel, then click `Settings`.
Within settings select `Shared Drives` and then tick all of the drives you wish
to be able to use within Docker containers. For this guide to work you will
at least need to share the drive where you will be keeping the QATrack+ server
files.

Docker for Windows does not support network drives.

### Ubuntu 18.04

If your PC is running Ubuntu 18.04 follow these steps to install the required
prerequisites.

#### Docker and Docker-Compose

To run this installation method you will need both docker-ce and docker-compose
on your system. When running Ubuntu 18.04 do this by running the following
commands:

```bash
sudo snap install docker

sudo apt install virtualenv
virtualenv -p python3 ~/.docker-compose
source ~/.docker-compose/bin/activate
pip install docker-compose
```

Each time before using the `docker-compose` command you will need to repeat the
above command of `source ~/.docker-compose/bin/activate`.

On other systems you can follow the instructions found at the following
locations:

* [docker-ce](https://docs.docker.com/install/)
* [docker-compose](https://docs.docker.com/compose/install/#install-compose)

##### Make docker work without sudo on Linux

You will also need to implement the following to be able to run docker without
sudo:

* <https://docs.docker.com/engine/installation/linux/linux-postinstall/>

After completing these post install tasks please reset your computer.

Before continuing please verify that you can run `docker run hello-world` in a
terminal.

#### Git

To retrieve files from bitbucket you will need git installed by running the
following:

```bash
sudo apt install git
```

On other systems follow the instructions at
<https://www.atlassian.com/git/tutorials/install-git>.

## Installing QATrack+

This part is OS independent. The language used will be tuned for a Windows 10
user, but equivalent steps can be followed on Ubuntu.

### Changing to the directory where all server files will be stored

Open a command prompt with just user priveledges and change your directory to the directory where
all of the QATrack+ server files will be stored.

Lets say, for example, all our files are going to be located within the
`D:` drive at `D:\QATrack+` then we would want to do the following:

```cmd
D:
cd QATrack+
```

### Downloading

At this point QATrack plus files need to be pulled from the git repository.
Do the following:

```cmd
git clone https://bitbucket.org/SimonGBiggs/qatrackplus.git
cd qatrackplus
git checkout simon-docker
```

### Installation

To run any `docker-compose` commands you need to be within the
`qatrackplus\deploy\docker` directory. So lets change to there now:

```cmd
cd deploy\docker
```

To build and start the server run the
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

With all default settings within Docker left as is, this will now automatically
start the server each time the computer is turned on.

### Setting up copying backups from local machine to remote server on Windows

Create the following bat file:

```batch
NET USE V: "\\pdc\OneDrive$\QATrack+"

xcopy D:\QATrack+\qatrackplus\deploy\docker\user-data\backup-management V:\ /E /G /H /D /Y
```

Then using Windows Task scheduler to set that bat file to run daily.

## Advanced usage tips 

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

### Setting up SSL

To set up SSL I highly recommending using CloudFlare's free 'one-click ssl'
which will set up SSL security between your users and CloudFlare:

> <https://www.cloudflare.com/ssl/>

To also secure
the path between CloudFlare and your server you will need to follow the
following steps:

> <https://support.cloudflare.com/hc/en-us/articles/217471977>

The `nginx.conf` file referred to by that guide is contained within this
directory. Place the certificate files within `user-data/ssl` then
they will be available at `/root/ssl/your_certificate.pem` and
`/root/ssl/your_key.key` on the server.

To reset the server and use your updated `nginx.cong` file run:

```bash
docker-compose stop
docker-compose up
```

### Changing from port 80 to a different port

The first number of the `ports` item within `docker-compose.yml` can be changed
to use a port that is different to port 80. For example, if `80:80` was changed
to `8080:80` then you would need to type <http://localhost:8080> within your
browser to see QATrack+. After editing `docker-compose.yml` you need to rerun
`docker-compose up`.

### Using a docker-hub image instead of building your own

If you don't wish to customise the python-virtual environment being used by
the server, and if you want to not have to build your own docker image you may
use the prebuilt automated builds off of [Docker Hub](https://hub.docker.com/r/simonbiggs/qatrack/builds/).

To do this change your directory to the subdirectory `hub/0.3.0.dev` and then
run `docker-compose up`. This will now also download the django portion of
QATrack+ from Docker Hub with the pip dependencies already included within the
image.

### Making the backup management store its files on a network share

Within the docker image all backup data is placed at
`/usr/src/qatrackplus/deploy/docker/user-data/backup-management`.
If during the initial boot of the docker image a network drive is mounted to
that directory theoretically all backups should be managed on that network
drive instead. To achieve this, at the start of `init.sh` write the following
line:

```bash
mount -t cifs -o username=your_user_name -o password=your_password //host_name/share_name /usr/src/qatrackplus/deploy/docker/user-data/backup-management
```

See [cifs man page](https://www.systutorials.com/docs/linux/man/8-mount.cifs/)
for more help if needed.

This has not been tested yet, please inform me if you have issues / if you get
it working.

### Shutdown the server

To shutdown the server run:

    docker-compose stop

You can also single press `Ctrl + C` within the server terminal that you ran
`docker-compose up` to gracefully shutdown the server.

### Update server

To update the server from bitbucket run:

    docker-compose stop
    git pull

Once any files have changed in the qatrackplus directory you need to run the following:

    docker-compose build
    docker-compose up

### Backup management

Everytime `docker-compose up` is run a timestamped backup zip file of the
database, uploaded files, and your site specific css is created. These backups
are stored within `qatrackplus/deploy/docker/user-data/backup-management/backups`.
To restore a backup zip file copy it to the restore directory found at
`qatrackplus/deploy/docker/user-data/backup-management/restore`.
The restoration will occur next time `docker-compose up` is called. After
successful restoration the zip file within the restore directory is deleted.

This restore method will also successfully restore backup files created on a
different machine. However it will only successfully restore a like for like
QATrack+ version. This cannot be used when upgrading between versions.

### Delete docker data

If for some reason you need it, the following command will delete all docker
data from all docker projects (WARNING, IRREVERSABLE):

```bash
docker stop $(docker ps -a -q) && docker rm $(docker ps -a -q)
```

And this will delete all of the cache:

```bash
echo 'y' | docker volume prune
```

To just delete all postgres database data do the following:

```bash
docker stop docker_qatrack-postgres_1 && docker rm docker_qatrack-postgres_1 && docker volume rm docker_qatrack-postgres-volume
```