CREATE USER 'qatrack_reports'@'localhost' IDENTIFIED BY 'qatrackpass';
GRANT SELECT ON qatrackplus.* to 'qatrack_reports'@'localhost';
