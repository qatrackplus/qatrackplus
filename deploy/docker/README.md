# QATrack+ Docker Deployment

This folder contains the Docker configuration for running QATrack+ in a modern, production-ready environment using Docker Compose V2.

## Directory Layout
- `compose.yaml`: The production-ready defaults.
- `compose.override.yaml`: Development overrides (e.g., binding local source code).
- `django/`: Multi-stage Dockerfile and entrypoint script for the Django app.
- `nginx/`: NGINX configuration and server blocks.
- `backup/`: A lightweight Alpine container that automatically runs database and media backups via cron.

For more information on the docker deployment, please refer to the official docs.

The docker documentation is found under `docs/install/docker.rst`.
