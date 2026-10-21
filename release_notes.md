# QATrack+ Release Notes #

Release notes are located at http://docs.qatrackplus.com/en/latest/release_notes.html

## v4.0.2

* **Docker**: Docker images no longer contain your `.env` file, local settings, uploaded files or database dumps. Rebuild any QATrack+ image you have copied to a registry or another machine.
* **Docker**: Database dumps in `deploy/docker/backups/` and new `.env` files (other than the `.env.example` templates) are now ignored by git. `deploy/docker/.env` is still tracked, so changes to it can still be committed.
* **Docker**: Files under `deploy/docker` always check out with LF line endings, including on Windows.

## v4.0.0 Recent Fixes

* **Service Log**: Service Event Templates can now be shared across different machines and modalities. When selecting a template, only the Return to Service tests that apply to the chosen unit will be added to the form ([#829](https://github.com/qatrackplus/qatrackplus/issues/829)).
* **QA**: Fixed an issue where resuming an autosaved QC session could display the wrong start date and time.
