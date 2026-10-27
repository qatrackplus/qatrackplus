# QATrack+ Docker Deployment

This folder contains the Docker configuration for running QATrack+ in a modern, production-ready environment using Docker Compose V2.

## Directory Layout
- `compose.yaml`: The production-ready defaults.
- `compose.dev.yaml`: Development overlay that runs your checkout instead of the image's code. Not applied automatically.
- `compose.db-port.yaml`: Optional overlay that publishes PostgreSQL on `127.0.0.1` for a database client or an SSH tunnel. Off unless turned on in `.env`; see `.env.example`.
- `django/`: Multi-stage Dockerfile and entrypoint script for the Django app.
- `nginx/`: NGINX image. It writes its server configuration at startup from `.env` (`ALLOWED_HOSTS`, `HTTP_OR_HTTPS` and the `NGINX_*` settings).
- `backup/`: A lightweight Alpine container that automatically runs database and media backups via cron.

## How to Run

### 1. Environment Setup
1. Copy the provided `.env.example` to `.env`.
   ```bash
   cp .env.example .env
   ```
2. Set your PostgreSQL credentials in the `.env` file. 
3. Set `ALLOWED_HOSTS` in your `.env` file to include the IP address or hostname you will use to access the server (e.g. `ALLOWED_HOSTS=qatrack.myclinic.ca,10.0.0.5`). To allow all hosts temporarily, use `ALLOWED_HOSTS=*`.
4. Every other setting (email, time zone, HTTPS, LDAP, ...) is optional and documented in `.env.example`. Keep `USE_DOCKER=true`: it tells QATrack+ to read its settings from `.env`.

`.env` holds your passwords and is ignored by git. Sites upgrading from 4.0.0 or 4.0.1, where it was tracked, follow the steps in the Docker upgrade guide before their first `git pull`.

### 2. Production
1. Configure strong, secure passwords in your `.env` file.
2. Build and start the containers:
   ```bash
   docker compose up -d --build
   ```
   This runs the QATrack+ code built into the image, as an unprivileged user. The `django-q` service runs scheduled notifications and reports.
3. To serve over HTTPS, copy `cert.pem` (full chain) and `key.pem` into `user-data/ssl` (with `sudo`: Docker creates that folder as root), set `HTTP_OR_HTTPS=https` in `.env`, and run `docker compose up -d`.
4. Uploaded files, log files and the generated secret key are kept in Docker volumes, and backups in `backups/`. To keep any of them in a folder on the server instead, set `QATRACK_MEDIA_DIR`, `QATRACK_LOGS_DIR`, `QATRACK_USER_DATA_DIR` or `QATRACK_BACKUPS_DIR` in `.env` (see `.env.example`). On a site already in use, copy the data across first, as "Keeping QATrack+'s data in folders on the server" in the Docker installation guide shows.

### 3. Development
`compose.dev.yaml` mounts your checkout into the container so code changes show up without rebuilding. It is not applied automatically. QATrack+ writes into your checkout, so it runs as your own user: add your ids to `.env` once, then use both files on every command.
```bash
printf '\nQATRACK_UID=%s\nQATRACK_GID=%s\n' "$(id -u)" "$(id -g)" >> .env
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

### 4. First Run Setup
When booting a fresh database for the first time, you must create a superuser (admin) account. With the containers running, open a new terminal window and execute:
```bash
docker compose exec django python manage.py createsuperuser
```
Follow the interactive prompts to set your username, email, and password.
