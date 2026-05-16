#    Copyright 2018 Simon Biggs

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os

print("Running docker settings")

ALLOWED_HOSTS = ["*"]

DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

SECRET_FILEPATH = "deploy/docker/user-data/secret_key.txt"

# Prefer environment variable for SECRET_KEY, fallback to file-based key for backward compatibility
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    try:
        with open(SECRET_FILEPATH, "r") as f:
            SECRET_KEY = f.read().strip()
    except IOError:
        import secrets

        SECRET_KEY = secrets.token_urlsafe(64)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(SECRET_FILEPATH), exist_ok=True)
        with open(SECRET_FILEPATH, "w") as f:
            f.write(SECRET_KEY)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "postgres"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "qatrack-postgres"),
        "PORT": int(os.environ.get("POSTGRES_PORT", 5432)),
    }
}
