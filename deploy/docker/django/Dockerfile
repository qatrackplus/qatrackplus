# syntax=docker/dockerfile:1.9

# Note:
# Inspired from https://hynek.me/articles/docker-uv/
# and https://github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile

ARG BUILDER_BASE_IMAGE="ghcr.io/astral-sh/uv:0.12-python3.12-trixie-slim"
ARG RUNTIME_BASE_IMAGE="python:3.12-slim-trixie"
# It is important to use the image that matches the uv builder image below,
# as the path to the Python executable must be the same, e.g.,
# using `python:3.11-slim-trixie` will fail if uv:python3.12-trixie-slim is used.
#
# If you need to, you can override the base images by setting the
# BUILDER_BASE_IMAGE and RUNTIME_BASE_IMAGE env vars in the .env file.

# Builder stage
FROM ${BUILDER_BASE_IMAGE} AS builder

SHELL ["sh", "-exc"]

# By default, omit development dependencies
ARG UV_NO_DEV=1
ENV UV_NO_DEV=${UV_NO_DEV}

# - Silence uv complaining about not being able to use hard links.
# - Tell uv NOT to byte-compile packages. Slightly longer startup, but reduced image size.
ENV UV_COMPILE_BYTECODE=0 UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

# Ensure apt-get doesn't open a menu on you.
ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update -y &&\
    apt-get upgrade -y &&\
    apt-get install -y \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    build-essential \
    ldap-utils \
    libldap2-dev \
    libsasl2-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Define virtual env directory
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Create venv.
# Make sure the created venv includes pip.
# We later use pip to install user requirements.
# Some user requirements might not be packaged as wheels -- thus uv pip might not
# be able to install them.
RUN uv venv --seed ${UV_PROJECT_ENVIRONMENT}

# Synchronize dependencies without the application itself.
# This layer is cached until uv.lock or pyproject.toml change, which are
# only temporarily mounted into the build container since we don't need
# them in the production one.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --extra docker --extra postgres --extra ldap

# Copy QATrack+ source
WORKDIR /app
COPY . .

# Install QATrack+ itself in editable mode, with the source under /app
# This layer's cache is busted each time the source of the app changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra docker --extra postgres --extra ldap

# Install user-specified dependencies, if any.
#
# First, we export all core dependencies to a constraint file.
# For this purpose, we do not emit hashes, as if we do so, pip will require
# hashes for the user-requirements/requirements.txt file.
RUN uv export \
    --frozen \
    --no-emit-project \
    --no-hashes \
    --extra docker \
    --extra postgres \
    --format requirements-txt \
    --output-file /tmp/core-constraints.txt

# Second, we install the user dependencies using pip, if any, respecting the
# core qatrack dependency version constraints.
COPY ./deploy/docker/user-requirements/ /tmp/user-requirements/
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ -s /tmp/user-requirements/requirements.txt ]; then \
    echo "Installing user requirements..." \
    && /opt/venv/bin/pip install \
    --constraint /tmp/core-constraints.txt \
    --requirement /tmp/user-requirements/requirements.txt; \
    fi

# Make sure weasyprint is uninstalled. If it's installed, then it will be used instead of chromium for HTML-to-PDF conversion.
RUN /opt/venv/bin/pip uninstall -y weasyprint || true

# Runtime stage without uv installed
FROM ${RUNTIME_BASE_IMAGE}

ARG HOST_UID=999
ARG HOST_GID=999

# Setup a non-root user
RUN groupadd --system --gid ${HOST_GID} user \
 && useradd --system --gid ${HOST_GID} --uid ${HOST_UID} --create-home user

# Ensure apt-get doesn't open a menu on you.
ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,sharing=locked,target=/var/cache/apt \
    apt-get update -y &&\
    apt-get upgrade -y &&\
    apt-get install -y \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    # postgres connectivity
    libpq5 \
    # for healthcheck
    curl \
    procps \
    # for converting files written on Windows
    dos2unix \
    # for LDAP support
    libldap2 \
    libsasl2-2 \
    # for converting HTML to PDF
    chromium \
    # For debugging in the container
    nano \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# Activate venv
ENV PATH="/opt/venv/bin:$PATH"

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Set MPLCONFIGDIR to stop matplotlib from complaining
ENV MPLCONFIGDIR=/home/user/.config/matplotlib

WORKDIR /app

# Copy
COPY --chown=user:user . .

# Move entrypoint to /, change its ownership to root
COPY --chown=root:root ./deploy/docker/django/entrypoint.sh /entrypoint.sh

# Ensure necessary directories exist: ./logs, ./qatrack/media and ./qatrack/static
# Make entrypoint executable
RUN dos2unix /entrypoint.sh \
    && chmod 755 /entrypoint.sh \
    && mkdir -p /home/user/.config/matplotlib \
                /home/user/.cache \
                ./logs \
                /app_data/media \
                /app_data/static \
                /user_data \
    && chown -R user:user /home/user \
                                ./logs \
                                /app_data/media \
                                /app_data/static \
                                /user_data

USER user

# Set some XDG variables for chromium
ENV XDG_RUNTIME_DIR=/tmp/xdg-runtime-user
ENV XDG_CONFIG_HOME=/home/user/.config
ENV XDG_CACHE_HOME=/home/user/.cache

EXPOSE 8000

CMD ["/entrypoint.sh"]
