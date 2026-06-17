CREATE USER 'qatrack_reports'@'localhost' IDENTIFIED BY 'qatrackpass';
GRANT SELECT ON qatrackplus40.* to 'qatrack_reports'@'localhost';
