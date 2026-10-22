"""The persisted SECRET_KEY: created once, adopted by everyone, never empty.

Only the Docker deployment generates its own key, and if two processes ever
settle on different keys - or one of them reads a half-written file - the
symptom is users being signed out at random with nothing in the logs to say
why. So the race is tested rather than reasoned about.
"""

import multiprocessing
import os
import pathlib
import stat
import tempfile
import unittest

from qatrack.qatrack_core.secret_key import (
    GENERATED_NOTICE,
    SecretKeyError,
    load_or_create,
)


def _worker(path):
    """Run in a forked process, so the OS arbitrates the race for real."""
    try:
        return load_or_create(path, announce=lambda message: None)
    except SecretKeyError as e:  # pragma: no cover - a failure to report
        return "ERROR: %s" % e


class TestSecretKeyFile(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.path = pathlib.Path(self.directory, "secrets", "secret_key.txt")
        self.notices = []

    def load(self):
        return load_or_create(self.path, announce=self.notices.append)

    def test_creates_a_key_and_persists_it(self):
        first = self.load()
        assert first
        assert self.path.read_text(encoding="utf-8").strip() == first
        assert self.load() == first

    @unittest.skipUnless(
        os.name == "posix",
        "Windows has no POSIX mode bits - it reports 0o666 for this file - and "
        "the key is only ever created in the Docker deployment, which is Linux",
    )
    def test_the_file_and_its_directory_are_private(self):
        self.load()
        assert stat.S_IMODE(self.path.stat().st_mode) == 0o600
        assert stat.S_IMODE(self.path.parent.stat().st_mode) == 0o700

    def test_generating_says_so_once(self):
        """Losing the key signs everybody out; that cannot be silent."""
        self.load()
        assert len(self.notices) == 1
        assert "generated" in self.notices[0]
        assert "sign in again" in self.notices[0]
        self.load()
        assert len(self.notices) == 1, "reading an existing key is not news"

    def test_notice_names_the_file(self):
        self.load()
        assert str(self.path) in self.notices[0]
        assert GENERATED_NOTICE.count("%s") == 1

    def test_whitespace_around_a_key_is_ignored(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("  a-key-with-whitespace\n", encoding="utf-8")
        assert self.load() == "a-key-with-whitespace"
        assert self.notices == []

    def test_an_empty_file_refuses_rather_than_replacing_it(self):
        """Generating here would silently invalidate every session."""
        self.path.parent.mkdir(parents=True)
        self.path.write_text("", encoding="utf-8")
        with self.assertRaises(SecretKeyError) as caught:
            self.load()
        assert "empty" in str(caught.exception)
        assert str(self.path) in str(caught.exception)
        assert self.path.read_text(encoding="utf-8") == "", "must not overwrite"

    @unittest.skipUnless(
        os.name == "posix",
        "Windows ignores POSIX mode bits on directories, so chmod 0o500 does not "
        "make one unwritable and there is nothing here to provoke",
    )
    def test_a_read_only_location_explains_itself(self):
        """django-q mounts /user_data read-only; django creates the key.

        POSIX only, and that is the whole scope of the behaviour: the read-only
        mount this message exists for is a Docker one, and the Docker
        deployment is Linux.
        """
        self.path.parent.mkdir(parents=True)
        os.chmod(self.path.parent, 0o500)
        try:
            with self.assertRaises(SecretKeyError) as caught:
                self.load()
        finally:
            os.chmod(self.path.parent, 0o700)
        message = str(caught.exception)
        assert "cannot create one" in message
        assert "django-q" in message, "name the service that cannot write"
        assert "SECRET_KEY" in message, "offer the way out"

    def test_no_temporary_file_is_left_behind(self):
        self.load()
        assert sorted(p.name for p in self.path.parent.iterdir()) == [
            "secret_key.txt"
        ]

    @unittest.skipUnless(
        "fork" in multiprocessing.get_all_start_methods(),
        "needs fork, so POSIX only; the race is between processes in one "
        "container, which is a Linux deployment",
    )
    def test_racing_processes_all_end_up_with_one_key(self):
        """django, django-q and several gunicorn workers start together.

        The earlier implementation created the file at its final name with
        O_EXCL and then wrote into it, so a loser could read it while it was
        still empty - and an empty SECRET_KEY is the one value that must never
        reach Django. Eight forked processes is enough to hit that window
        when it exists.
        """
        context = multiprocessing.get_context("fork")
        with context.Pool(8) as pool:
            results = pool.map(_worker, [self.path] * 8)

        assert all(not str(r).startswith("ERROR") for r in results), results
        assert all(results), "an empty key was handed out"
        assert len(set(results)) == 1, "processes disagreed: %r" % set(results)
        assert self.path.read_text(encoding="utf-8").strip() == results[0]
