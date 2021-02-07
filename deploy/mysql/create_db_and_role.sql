CREATE USER 'qatrack'@'localhost' IDENTIFIED BY 'qatrackpass';
CREATE DATABASE qatrackplus031;
GRANT ALL ON qatrackplus031.* TO 'qatrack'@'localhost';
flush privileges;

