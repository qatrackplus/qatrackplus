CREATE USER qatrack WITH PASSWORD 'qatrackpass';
CREATE DATABASE qatrackplus OWNER qatrack;
GRANT ALL PRIVILEGES ON DATABASE qatrackplus to qatrack;
