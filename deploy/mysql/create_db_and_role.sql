CREATE USER 'qatrack'@'localhost' IDENTIFIED BY 'qatrackpass';
CREATE DATABASE qatrackplus40 CHARACTER SET utf8mb4;
GRANT ALL ON qatrackplus40.* TO 'qatrack'@'localhost';
flush privileges;

