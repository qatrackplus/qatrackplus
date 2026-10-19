# QATrack+ Release Notes #

Release notes are located at http://docs.qatrackplus.com/en/latest/release_notes.html

## v4.0.0 Recent Fixes

* **Service Log**: Service Event Templates can now be shared across different machines and modalities. When selecting a template, only the Return to Service tests that apply to the chosen unit will be added to the form ([#829](https://github.com/qatrackplus/qatrackplus/issues/829)).
* **QA**: Fixed an issue where resuming an autosaved QC session could display the wrong start date and time.
* **Docker**: `docker compose up` no longer gives up on a first install or upgrade while the django service is still running its database migrations (which left the web server unstarted); django now has up to 10 minutes to start.
