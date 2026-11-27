# Release notes waiting for a release

If you think your pull request could be user-facing, add a release note as one
file here. Leave `release_notes.md` alone: one file per pull request means two of
them never conflict.

    changes/<user>_<purpose>.md

- `<user>` is your GitHub handle, for example `nsmela`.
- `<purpose>` is a short lowercase slug with hyphens, for example `docker-port`. No
  underscores: one separates the two parts.

The file holds one or more bullets, written as they will appear in
`release_notes.md`, with no heading:

    * **Docker**: Signing in works on a site published on a port other than 80 or 443 ([#915](https://github.com/qatrackplus/qatrackplus/issues/915)).

To correct a note before its release, edit its file.

## At a release

The release manager moves every file's bullets under the new version's heading in
`release_notes.md` and deletes the files, in one commit. A pull request picked
onto a release branch brings its file with it, so its note is merged there, at
that branch's next release.

`qatrack/qatrack_core/tests/test_release_note_files.py` checks the file names and
that each file holds at least one bullet. The *Release notes* workflow fails a pull
request that adds bullets or headings to `release_notes.md` unless it also deletes
every file here, which only a release does.
