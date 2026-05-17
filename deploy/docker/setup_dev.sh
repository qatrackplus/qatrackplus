#!/bin/bash
# set -e  # Disable exit on error for fixture loading to handle partial existing data

# Generate local_settings.py from environment variables if not present
if [ ! -f qatrack/local_settings.py ]; then
    cat > qatrack/local_settings.py << EOF
SECRET_KEY = '${SECRET_KEY:-dev-insecure-key-not-for-production}'
DEBUG = True
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['http://localhost:8080', 'http://localhost:8000']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '${POSTGRES_DB:-qatrackdb}',
        'USER': '${POSTGRES_USER:-qatrack}',
        'PASSWORD': '${POSTGRES_PASSWORD:-qatrack}',
        'HOST': '${POSTGRES_HOST:-qatrack-postgres}',
        'PORT': 5432,
    }
}
EOF
    echo "Created qatrack/local_settings.py"
fi

echo "Starting dev environment setup..."

# Wait for postgres to be ready
echo "Waiting for postgres..."
until pg_isready -h qatrack-postgres -p 5432 -U qatrack; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done

echo "Postgres is ready. Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating cache table..."
python manage.py createcachetable

echo "Creating superuser..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("Superuser created successfully.")
else:
    print("Superuser already exists.")
EOF

echo "Loading fixtures..."
# We use a loop and || true to ensure that if some fixtures fail (e.g. duplicates), 
# the script continues to load the rest.
echo "Loading QA fixtures..."
for f in fixtures/defaults/qa/*.json; do
    echo "Loading $f"
    python manage.py loaddata "$f" || echo "Warning: Failed to load $f (it might already exist)"
done

echo "Loading Service Log fixtures..."
for f in fixtures/defaults/service_log/*.json; do
    echo "Loading $f"
    python manage.py loaddata "$f" || echo "Warning: Failed to load $f (it might already exist)"
done

echo "Loading Unit fixtures..."
for f in fixtures/defaults/units/*.json; do
    echo "Loading $f"
    python manage.py loaddata "$f" || echo "Warning: Failed to load $f (it might already exist)"
done

echo "Dev environment setup complete!"
