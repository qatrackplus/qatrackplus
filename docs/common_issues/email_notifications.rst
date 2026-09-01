.. _email_notifications:

Email Notification Issues
=========================

This page collects problems related to QATrack+ email notifications not being
sent or not being received.

----

.. _email_not_sending:

Emails Are Not Being Sent
--------------------------

**Symptom**

QATrack+ should send email notifications (e.g. due/overdue QC alerts) but
users never receive them. No error is visible in the application.

**Cause**

The email backend is not configured, the SMTP credentials are wrong, or the
background task that sends emails is not running.

**Solution**

1. Confirm the email settings in ``local_settings.py``::

      EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
      EMAIL_HOST = 'smtp.example.com'
      EMAIL_PORT = 587
      EMAIL_USE_TLS = True
      EMAIL_HOST_USER = 'qatrack@example.com'
      EMAIL_HOST_PASSWORD = 'your-password'
      DEFAULT_FROM_EMAIL = 'qatrack@example.com'

2. Test the email configuration from the Django shell::

      python manage.py shell
      >>> from django.core.mail import send_mail
      >>> send_mail('Test', 'Test body', 'from@example.com', ['to@example.com'])

   If this raises an exception, fix the SMTP settings.

3. Confirm that the ``huey`` background task worker is running. On Linux with
   systemd::

      sudo systemctl status huey

   Restart it if stopped::

      sudo systemctl restart huey

4. Check the QATrack+ notification configuration under
   **Admin › Notifications** to ensure notifications are configured and
   active.

**See also**

* `Django email documentation <https://docs.djangoproject.com/en/stable/topics/email/>`_
* :ref:`QATrack+ notifications <notifications>`

----

.. _email_in_spam:

Emails Arrive in Spam
----------------------

**Symptom**

Notification emails are sent but land in the recipient's spam or junk folder.

**Cause**

The sending domain does not have correct SPF, DKIM, or DMARC DNS records, or
the ``DEFAULT_FROM_EMAIL`` address doesn't match the SMTP account.

**Solution**

1. Ensure ``DEFAULT_FROM_EMAIL`` uses an address that belongs to the domain
   configured on the SMTP server.

2. Work with your IT department to configure SPF and DKIM records for the
   sending domain.

3. As a quick workaround, use an established email relay service (Gmail
   Workspace, SendGrid, Mailgun, etc.) as the SMTP backend — these services
   have strong sender reputations.

----

.. _email_ssl_error:

SSL/TLS Error When Sending Email
----------------------------------

**Symptom**

Email sending fails with::

   ssl.SSLError: [SSL: WRONG_VERSION_NUMBER] wrong version number

or::

   smtplib.SMTPException: STARTTLS extension not supported by server.

**Cause**

The ``EMAIL_USE_TLS`` / ``EMAIL_USE_SSL`` settings don't match the SMTP
server's requirements.

**Solution**

Typical port/TLS combinations:

* Port **587** → ``EMAIL_USE_TLS = True``, ``EMAIL_USE_SSL = False``
* Port **465** → ``EMAIL_USE_TLS = False``, ``EMAIL_USE_SSL = True``
* Port **25**  → ``EMAIL_USE_TLS = False``, ``EMAIL_USE_SSL = False``

Update ``local_settings.py`` to match your SMTP server's requirements and
restart QATrack+.
