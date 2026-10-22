# QATrack+ Release Notes #

Release notes are located at http://docs.qatrackplus.com/en/latest/release_notes.html

## v4.0.2

* **Docker**: `deploy/docker/.env` is no longer tracked by git, because it holds your database password. Before your first `git pull` to 4.0.2, copy your `.env` aside and back as described in the Docker upgrade guide; later pulls leave it alone.
* **Docker**: QATrack+'s settings (email, time zone, HTTPS, sessions, QC display options, ADFS, Active Directory / LDAP and more) can now be set in `deploy/docker/.env`; `.env.example` documents each one. The image now includes LDAP support.
* **Docker**: Upgrades no longer sign every user out: a generated secret key is now kept in a volume, or taken from `SECRET_KEY` in `.env`.
* **Docker**: Scheduled notifications, scheduled reports and the emails they send now run: a new `django-q` service runs QATrack+'s background tasks, which Docker installations had no process for.
* **Docker**: HTTPS works: with `HTTP_OR_HTTPS=https` and your certificate in `deploy/docker/user-data/ssl`, nginx serves QATrack+ over HTTPS and redirects HTTP to it.
* **Docker**: nginx answers only the hosts in `ALLOWED_HOSTS`, accepts uploads up to 100 MB (was 1 MB), and every service's logs are capped at 50 MB.
* **Docker**: The QATrack+ application container no longer runs as root. Existing media and static files are re-owned automatically on the next `docker compose up -d`; the commands you run do not change.
* **Docker**: `compose.override.yaml` is now `compose.dev.yaml` and is no longer applied automatically, so plain `docker compose` runs the code built into the image. Developers use `docker compose -f compose.yaml -f compose.dev.yaml` with their own ids in `.env`. QATrack+ log files are now inside the container (`docker compose logs django`).
* **Docker**: The Docker image installs exactly the dependency versions in `uv.lock`, the same versions the test suite runs against.
* **Docker**: Docker images no longer contain your `.env` file, local settings, uploaded files or database dumps. Rebuild any QATrack+ image you have copied to a registry or another machine.
* **Docker**: Database dumps in `deploy/docker/backups/` and `.env` files (other than the `.env.example` templates) are now ignored by git.
* **Docker**: Files under `deploy/docker` always check out with LF line endings, including on Windows.

## v4.0.0 Recent Fixes

* **Service Log**: Service Event Templates can now be shared across different machines and modalities. When selecting a template, only the Return to Service tests that apply to the chosen unit will be added to the form ([#829](https://github.com/qatrackplus/qatrackplus/issues/829)).
* **QA**: Fixed an issue where resuming an autosaved QC session could display the wrong start date and time.
