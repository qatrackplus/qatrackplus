# Stands in for the "site-requirements" build context when a build does not
# give one (compose.yaml always does): an empty folder, so no site packages.
# `docker build --build-context site-requirements=deploy/docker/site-requirements`
# gives it without compose.
FROM scratch AS site-requirements

# Builder stage: install the locked dependencies into /opt/venv
FROM python:3.12-slim-bookworm AS builder

# libldap2-dev and libsasl2-dev: python-ldap builds from source on Linux
RUN apt-get update && apt-get install -y \
    build-essential \
    libldap2-dev \
    libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

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
    uv sync --frozen --no-dev --no-install-project --extra docker --extra postgres --extra ldap

# A site's own packages, from deploy/docker/site-requirements (see the README
# there). compose.yaml passes that folder in as a separate build context named
# "site-requirements", so it is never part of the main context (see
# .dockerignore) and nothing in it - a requirements file holding a private index
# token, large wheel files - is copied into the image by the runtime stage.
# Built without compose, the empty stage at the top stands in for it and no site
# packages are installed.
#
# QATrack+'s own packages, exactly as installed above, are the constraints, so a
# package that needs a different version of one of them fails the build instead
# of changing what QATrack+ runs on.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,from=site-requirements,target=/tmp/site-requirements \
    if [ -s /tmp/site-requirements/requirements.txt ]; then \
        uv pip freeze --python /opt/venv/bin/python > /tmp/qatrack-constraints.txt \
        && uv pip install --python /opt/venv/bin/python \
            --constraint /tmp/qatrack-constraints.txt \
            --find-links /tmp/site-requirements \
            --requirement /tmp/site-requirements/requirements.txt; \
    fi

# Runtime stage
FROM python:3.12-slim-bookworm

# libldap-common provides /etc/ldap/ldap.conf, which points LDAP at the system
# CA store (/etc/ssl/certs/ca-certificates.crt). That is what lets Active
# Directory sign-in over LDAPS trust a directory whose certificate comes from a
# public CA, with no AD_CERT_FILE. libldap-2.5-0 only recommends it, so it is
# listed here to keep it if recommended packages are ever left out.
#
# tzdata is here for the container's own tooling - `date`, the postgres client,
# anything reading /usr/share/zoneinfo. **Python does not read it**: this image
# sets PYTHONTZPATH= below, so `zoneinfo` uses the tzdata *package* pinned in
# uv.lock. That is deliberate, and it is why this layer being cached no longer
# matters - see the ENV block.
RUN apt-get update && apt-get install -y \
    postgresql-client \
    cifs-utils \
    chromium \
    libpq5 \
    curl \
    dos2unix \
    libldap-2.5-0 \
    libldap-common \
    libsasl2-2 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# QATrack+ runs as this unprivileged user. The nginx and backup images use the
# same uid/gid for the shared volumes, and compose.yaml's init service re-owns
# files left by earlier images, which ran as root.
RUN groupadd --gid 1000 qatrack \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/qatrack qatrack

COPY --from=builder /opt/venv /opt/venv
# USE_DOCKER is what settings.py keys off to read its configuration from the
# environment instead of importing local_settings.py, which this image does not
# contain. entrypoint.sh exports it, so the server has always had it - but a
# `docker compose exec` starts from the image's own configuration and does not,
# unless .env happens to set it. .env.example does, so the documented path works;
# a site that writes or trims .env by hand gets a stack that boots, passes its
# health check and serves requests, while every documented management command -
# createsuperuser, shell, check_unique_constraints - stops with
# "No module named 'qatrack.local_settings'", naming a file its admin has never
# heard of. Setting it here makes it true of the image, which it is: this image
# is only ever run under Docker.
# PYTHONTZPATH= empties zoneinfo's search path, so `zoneinfo` falls back to the
# tzdata PACKAGE instead of the operating system's copy.
#
# Why: Python reads the system database *before* the package, so on Linux the
# image's apt copy decided what every timestamp meant - and whether it was
# current depended on when the image happened to be built and whether a layer
# was cached. An image carrying tzdata 2026c was seen on 2026-11-04 with
# Manitoba still falling back on 1 November, which it no longer does. That made
# Docker the one platform where the rules were neither pinned nor tested.
#
# With this set, the image behaves like Windows, where there is no system
# database to read: the version in uv.lock is the single source, it is the
# version the test suite asserts against, and CI exercises the same one a site
# runs. `tzdata` is a declared runtime dependency for exactly this
# reason - with an empty TZPATH and no tzdata, every zone lookup raises
# ZoneInfoNotFoundError.
#
# Measured: with PYTHONTZPATH empty, zoneinfo.TZPATH is () and
# America/Winnipeg gives -0500 at 2026-11-04 from the package.
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONTZPATH="" \
    USE_DOCKER=true \
    MPLCONFIGDIR=/home/qatrack/.config/matplotlib

WORKDIR /usr/src/qatrackplus
# The source stays owned by root, so the app cannot modify its own code.
COPY . .

# Make entrypoint executable and move it out of the volume mount. init.sh is
# what compose.yaml's init service runs, as root, before django starts.
RUN cp deploy/docker/django/entrypoint.sh /entrypoint.sh && \
    cp deploy/docker/django/init.sh /init.sh && \
    dos2unix /entrypoint.sh /init.sh && \
    chmod 755 /entrypoint.sh /init.sh

# Directories the app writes to
RUN mkdir -p logs deploy/docker/user-data qatrack/media qatrack/static && \
    chown qatrack:qatrack logs deploy/docker/user-data qatrack/media qatrack/static

# settings.py creates this empty site-specific stylesheet on first import if it
# is missing. The app cannot write to the source tree, so create it here.
RUN css=qatrack/qatrack_core/static/qatrack_core/css/site.css && \
    [ -f "$css" ] || printf '/* You can place any site specific css in this file*/\n' > "$css"

# Numeric, so container runtimes can verify the image does not run as root
# without looking up the name inside it. 1000:1000 is the qatrack user above.
USER 1000:1000

EXPOSE 8000
CMD ["/entrypoint.sh"]
