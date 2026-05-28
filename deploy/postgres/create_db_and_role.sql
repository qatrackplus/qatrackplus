CREATE USER qatrack WITH PASSWORD 'qatrackpass';
CREATE DATABASE qatrackplus32;
\c qatrackplus32;
GRANT ALL PRIVILEGES ON DATABASE qatrackplus32 to qatrack;
GRANT ALL ON SCHEMA public TO qatrack;
ALTER USER qatrack CREATEDB;
--GRANT CREATE ON SCHEMA public TO qatrack;
-- SCHEMA public OWNER TO qatrack;


