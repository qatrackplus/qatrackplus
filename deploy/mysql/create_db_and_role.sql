CREATE USER qatrack;
CREATE DATABASE qatrackplus;
GRANT ALL ON qatrackplus.* TO 'qatrack'@'localhost' IDENTIFIED BY 'qatrackpass';

