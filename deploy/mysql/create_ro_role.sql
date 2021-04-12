CREATE USER 'qatrack_reports'@'localhost' IDENTIFIED BY 'qatrackpass';
GRANT SELECT ON qatrackplus31.* to 'qatrack_reports'@'localhost';
