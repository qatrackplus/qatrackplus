"""Limits in settings.py that keep a long-running server healthy."""
from django.conf import settings
from django.test import SimpleTestCase


class TestLogFilesRotate(SimpleTestCase):

    def test_every_log_file_has_a_size_limit(self):
        # A rotating handler with no maxBytes never rotates, so its file grows
        # until the disk is full.
        file_handlers = {
            name: handler for name, handler in settings.LOGGING['handlers'].items() if 'filename' in handler
        }
        self.assertTrue(file_handlers)
        for name, handler in file_handlers.items():
            with self.subTest(handler=name):
                self.assertGreater(handler.get('maxBytes', 0), 0)


class TestBackgroundTaskLimits(SimpleTestCase):

    def test_retry_is_longer_than_timeout(self):
        # django-q hands a task out again after `retry` seconds; a task allowed
        # to run longer than that would be run twice.
        self.assertGreater(settings.Q_CLUSTER['retry'], settings.Q_CLUSTER['timeout'])

    def test_timeout_allows_large_reports(self):
        # Scheduled reports render their PDFs in a task, and a large report can
        # take more than a minute.
        self.assertGreaterEqual(settings.Q_CLUSTER['timeout'], 300)
