python manage.py flush --no-input 
PGPASSWORD="qatrackpass" psql -U qatrack -d qatrackplus32 -c "TRUNCATE TABLE django_content_type CASCADE;"
python manage.py loaddata ~/web/qatrackplus/qatrack-dump.json

