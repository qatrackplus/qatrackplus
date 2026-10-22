"""Reading, and if need be creating, a persisted SECRET_KEY.

Stdlib only, and no Django imports: this runs from settings.py while the
settings module is still being assembled, so `django.conf`, the ORM and
logging are all unavailable.

Only the Docker deployment uses this. Every other install method carries its
key in `local_settings.py`, and a Docker deployment that sets `SECRET_KEY` in
its environment never reaches here either.
"""

import os
import pathlib
import secrets
import sys

KEY_BYTES = 64

GENERATED_NOTICE = (
    "SECRET_KEY: no key was found, so a new one was generated and saved to %s.\n"
    "SECRET_KEY: if this is not a new installation then the previous key has been "
    "lost, and every signed-in session and every outstanding password-reset link "
    "is now invalid. Users will have to sign in again.\n"
    "SECRET_KEY: back that file up, or set SECRET_KEY in the environment instead."
)


class SecretKeyError(Exception):
    """A secret key could neither be read nor created."""


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read().strip()


def _announce(message):
    # stderr, not logging: LOGGING is configured later in settings.py, so a
    # logger here would be the root logger with no handlers and the notice
    # would be swallowed. Container and service logs both capture stderr.
    print(message, file=sys.stderr)


def load_or_create(path, announce=_announce):
    """Return the persisted secret key at `path`, creating it if absent.

    Raises SecretKeyError when the file exists but is unusable, or when no key
    exists and this process cannot create one.
    """
    path = pathlib.Path(path)

    try:
        existing = _read(path)
    except FileNotFoundError:
        existing = None
    except OSError as e:
        raise SecretKeyError(
            "Could not read the secret key file %s: %s" % (path, e)
        ) from e
    else:
        if existing:
            return existing
        # An empty file is not a race any more - a key is published complete
        # or not at all (see below) - so it means the file was truncated or
        # created empty by hand. Generating a replacement would silently
        # invalidate every session, so refuse instead.
        raise SecretKeyError(
            "The secret key file %s is empty. Restore it from your backup, or "
            "delete it to have a new key generated - which will sign out every "
            "user and invalidate every outstanding password-reset link." % path
        )

    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as e:
        raise SecretKeyError(_cannot_create(path, e)) from e

    candidate = secrets.token_urlsafe(KEY_BYTES)
    temporary = path.with_name("%s.%d.tmp" % (path.name, os.getpid()))

    try:
        # Written to a temporary name and then published with os.link, rather
        # than created at the final name and written into: O_EXCL on the final
        # name makes an *empty* file visible to every other process for as long
        # as the write takes. A reader that opened it in that window got "",
        # which is the one value this module must never hand to Django. Readers
        # now see the final name only once it holds a whole key.
        #
        # os.link and not os.replace, because link fails rather than clobbering:
        # whoever loses the race keeps the winner's key, since two processes
        # using different keys is worse than either of them losing.
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(candidate)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            os.unlink(temporary)
            raise

        try:
            os.link(temporary, path)
        except FileExistsError:
            # Somebody published first. Their file is complete by construction.
            adopted = _read(path)
            if not adopted:
                raise SecretKeyError(
                    "Another process is writing the secret key file %s and it "
                    "is still empty. Set SECRET_KEY in the environment to take "
                    "this out of the start-up path." % path
                )
            return adopted
        except OSError as e:
            # Hard links are not available on every filesystem a volume might
            # be backed by. Rather than fall back to something that could
            # clobber a key, say so: adopt a key if one has appeared, and
            # otherwise send the operator to SECRET_KEY.
            adopted = ""
            try:
                adopted = _read(path)
            except OSError:
                pass
            if adopted:
                return adopted
            raise SecretKeyError(
                "Could not publish a new secret key at %s: %s. Set SECRET_KEY "
                "in the environment instead." % (path, e)
            ) from e
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:  # pragma: no cover - already gone
                pass
    except OSError as e:
        raise SecretKeyError(_cannot_create(path, e)) from e

    announce(GENERATED_NOTICE % path)
    return candidate


def _cannot_create(path, error):
    return (
        "No secret key was found at %s and this process cannot create one: %s. "
        "In the Docker deployment the django service creates the key and the "
        "django-q service mounts it read-only, so start django first - or set "
        "SECRET_KEY in the environment, which removes the need for the file "
        "altogether." % (path, error)
    )
