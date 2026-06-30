from django.apps import AppConfig


class QATrackCoreConfig(AppConfig):
    name = 'qatrack.qatrack_core'

    def ready(self):
        import qatrack.qatrack_core.checks  # noqa
