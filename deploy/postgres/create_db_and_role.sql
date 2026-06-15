CREATE USER qatrack WITH PASSWORD 'qatrackpass';
CREATE DATABASE qatrackplus40 OWNER qatrack;
GRANT ALL PRIVILEGES ON DATABASE qatrackplus40 to qatrack;
