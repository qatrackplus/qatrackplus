"""Host names QATrack+ treats specially.

Keep this module free of Django imports: qatrack/settings.py loads it, through
qatrack/docker_settings.py, before Django is set up.
"""

# The names a machine uses for itself. A request addressed to one comes from the
# server (a container health check, say), not from a person, so these are never
# what users type and never a link target.
LOOPBACK_HOSTS = ('localhost', '127.0.0.1')
