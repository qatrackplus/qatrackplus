# QATrack+ Release Notes #

Release notes are located at http://docs.qatrackplus.com/en/latest/release_notes.html

## v4.0.0 Recent Fixes

* **Service Log**: Service Event Templates can now be shared across different machines and modalities. When selecting a template, only the Return to Service tests that apply to the chosen unit will be added to the form ([#829](https://github.com/qatrackplus/qatrackplus/issues/829)).
* **QA**: Fixed an issue where resuming an autosaved QC session could display the wrong start date and time.
* **Installation**: The Linux install, upgrade and restore instructions now give the `logs` and `qatrack/media` folders to the local OS user for QATrack+ services, with `www-data` as the group, which fixes permission errors when uploading attachments to Service Events and Test Lists. Sites installed with the 4.0.0 instructions have a one-time fix in the 4.0.x upgrade guide, and `python manage.py check` now prints the exact commands to repair the folder ownership ([#836](https://github.com/qatrackplus/qatrackplus/issues/836)).
