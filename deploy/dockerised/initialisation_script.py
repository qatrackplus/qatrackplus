import socket
import os
import time

from glob import glob

from django.contrib.auth.models import User
from django.core.management import call_command


port = int(os.environ["DB_PORT"]) # 5432
database_name = os.environ["DB_NAME"]

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((database_name, port))
        s.close()
        break
    except socket.error as ex:
        time.sleep(0.1)


call_command('migrate')

all_users = User.objects.all()
if len(all_users) == 0:
    admin_user = os.getenv('ADMIN_USER', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')

    User.objects.create_superuser(admin_user, admin_email, admin_password)

    fixtures = glob('/usr/src/app/fixtures/defaults/*/*')
    for fixture in fixtures:
        call_command('loaddata', fixture)


call_command('collectstatic', '--noinput')
