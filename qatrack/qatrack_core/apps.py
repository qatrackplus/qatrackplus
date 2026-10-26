from django.apps import AppConfig


class QATrackCoreConfig(AppConfig):
    name = 'qatrack.qatrack_core'

    def ready(self):
        import qatrack.qatrack_core.checks  # noqa

        # Every configured language gets QATrack+'s date formats, including one
        # added after install. Without this, Django falls back to its own
        # locale formats for any language with no module under
        # FORMAT_MODULE_PATH, and the server then parses dates in a different
        # format from the one the page gave the browser - silently. See
        # qatrack/formats/__init__.py.
        from qatrack.formats import register_format_modules
        register_format_modules()
