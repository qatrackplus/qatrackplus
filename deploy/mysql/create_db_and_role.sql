CREATE USER 'qatrack'@'localhost' IDENTIFIED BY 'qatrackpass';
CREATE DATABASE qatrackplus CHARACTER SET utf8mb4;
GRANT ALL ON qatrackplus.* TO 'qatrack'@'localhost';
flush privileges;

