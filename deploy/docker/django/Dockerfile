# Builder stage: install the locked dependencies into /opt/venv
FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /usr/src/qatrackplus
# Exactly the versions in uv.lock. The project itself is not installed: the app
# runs from its source in the runtime stage.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project --extra docker --extra postgres

# Runtime stage
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y \
    postgresql-client \
    cifs-utils \
    chromium \
    libpq5 \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# QATrack+ runs as this unprivileged user. The nginx and backup images use the
# same uid/gid for the shared volumes, and compose.yaml's init service re-owns
# files left by earlier images, which ran as root.
RUN groupadd --gid 1000 qatrack \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/qatrack qatrack

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/home/qatrack/.config/matplotlib

WORKDIR /usr/src/qatrackplus
# The source stays owned by root, so the app cannot modify its own code.
COPY . .

# Make entrypoint executable and move it out of the volume mount
RUN cp deploy/docker/django/entrypoint.sh /entrypoint.sh && \
    dos2unix /entrypoint.sh && \
    chmod 755 /entrypoint.sh

# Directories the app writes to
RUN mkdir -p logs deploy/docker/user-data qatrack/media qatrack/static && \
    chown qatrack:qatrack logs deploy/docker/user-data qatrack/media qatrack/static

USER qatrack

EXPOSE 8000
CMD ["/entrypoint.sh"]
