# QATrack+ Docker Deployment

This folder contains the Docker configuration for running QATrack+ in a modern, production-ready environment using Docker Compose V2.

## Directory Layout
- `compose.yaml`: The production-ready defaults.
- `compose.override.yaml`: Development overrides (e.g., binding local source code).
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

### 2. Development
By default, Docker Compose will read both `compose.yaml` and `compose.override.yaml`. The override file maps your local source code into the container for live reloading.

Run the development environment:
```bash
docker compose up --build
```

### 3. Production
1. Review the NGINX TLS config in `nginx/conf.d/tls.conf.example`.
2. Configure strong, secure passwords in your `.env` file.
3. Start the containers using **only** the production file (ignoring the local code bind-mounts):
   ```bash
   docker compose -f compose.yaml up -d --build
   ```

### 4. First Run Setup
When booting a fresh database for the first time, you must create a superuser (admin) account. With the containers running, open a new terminal window and execute:
```bash
docker compose exec django python manage.py createsuperuser
```
Follow the interactive prompts to set your username, email, and password.
