python manage.py flush 
PGPASSWORD="qatrackpass" psql -U qatrack -d qatrackplus32 -c "TRUNCATE TABLE django_content_type CASCADE;"
python manage.py loaddata /home/najemm/web/qatrackplus/qatrack-dump.json

