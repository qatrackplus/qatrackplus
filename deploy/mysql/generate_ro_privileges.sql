SELECT 'DROP USER qatrack_reports@localhost;';
SELECT 'CREATE USER ''qatrack_reports''@''localhost'' IDENTIFIED BY ''qatrackpass'';';
SELECT
    CONCAT('GRANT SELECT ON ', table_name, ' TO qatrack_reports@localhost;')
FROM information_schema.tables
WHERE
    table_schema = 'qatrackplus31'
AND
    table_name not in ('django_session', 'auth_user', 'authtoken_token');
SELECT 'GRANT SELECT (id, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) ON auth_user TO qatrack_reports@localhost;';
