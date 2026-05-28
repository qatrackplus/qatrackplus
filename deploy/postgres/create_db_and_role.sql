CREATE USER qatrack WITH PASSWORD 'qatrackpass';
CREATE DATABASE qatrackplus31;
\c qatrackplus31;
GRANT ALL PRIVILEGES ON DATABASE qatrackplus31 to qatrack;
GRANT ALL ON SCHEMA public TO qatrack;
ALTER USER qatrack CREATEDB;
--GRANT CREATE ON SCHEMA public TO qatrack;
-- SCHEMA public OWNER TO qatrack;


