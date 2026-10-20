# QATrack+ Docker Deployment

This folder contains the Docker configuration for running QATrack+ in a modern, production-ready environment using Docker Compose V2.

## Directory Layout
- `compose.yaml`: The production-ready defaults.
- `compose.dev.yaml`: Development overlay that runs your checkout instead of the image's code. Not applied automatically.
- `django/`: Multi-stage Dockerfile and entrypoint script for the Django app.
- `nginx/`: NGINX configuration and server blocks.
- `backup/`: A lightweight Alpine container that automatically runs database and media backups via cron.

## How to Run

### 1. Environment Setup
1. Copy the provided `.env.example` to `.env`.
   ```bash
   cp .env.example .env
   ```
2. Set your PostgreSQL credentials in the `.env` file. 
3. Set `ALLOWED_HOSTS` in your `.env` file to include the IP address or hostname you will use to access the server (e.g. `ALLOWED_HOSTS=localhost,127.0.0.1,ubuntu-test`). To allow all hosts temporarily, use `ALLOWED_HOSTS=*`.
4. **CRITICAL:** Ensure `USE_DOCKER=true` is present in your `.env` file. This tells Django to use the built-in Docker configuration instead of falling back to your local SQLite configuration (`local_settings.py`).

### 2. Production
1. Configure strong, secure passwords in your `.env` file.
2. Build and start the containers:
   ```bash
   docker compose up -d --build
   ```
   This runs the QATrack+ code built into the image, as an unprivileged user.

### 3. Development
`compose.dev.yaml` mounts your checkout into the container so code changes show up without rebuilding. It is not applied automatically. QATrack+ writes into your checkout, so it runs as your own user: add your ids to `.env` once, then use both files on every command.
```bash
echo "QATRACK_UID=$(id -u)" >> .env
echo "QATRACK_GID=$(id -g)" >> .env
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

### 4. First Run Setup
When booting a fresh database for the first time, you must create a superuser (admin) account. With the containers running, open a new terminal window and execute:
```bash
docker compose exec django python manage.py createsuperuser
```
Follow the interactive prompts to set your username, email, and password.
