CREATE USER 'qatrack'@'localhost' IDENTIFIED BY 'qatrackpass';
CREATE DATABASE qatrackplus31 CHARACTER SET utf8;
GRANT ALL ON qatrackplus31.* TO 'qatrack'@'localhost';
flush privileges;

