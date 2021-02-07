GRANT CONNECT ON DATABASE qatrackplus031 TO qatrack_reports;
\c qatrackplus031
GRANT USAGE ON SCHEMA public TO qatrack_reports;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO qatrack_reports;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO qatrack_reports;
REVOKE SELECT ON "django_session" FROM qatrack_reports;
REVOKE SELECT ON "auth_user" FROM qatrack_reports;
REVOKE SELECT ON "authtoken_token" FROM qatrack_reports;
GRANT SELECT (id, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) ON "auth_user" TO qatrack_reports;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO qatrack_reports;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO qatrack_reports;
