import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import pynliner

logger = logging.getLogger('qatrack')


def send_email_to_users(
    recipients, template, context=None, subject_template=None, text_template=None, attachments=None
):

    if len(recipients) == 0:
        return

    attachments = attachments or []
    context = context or {}

    from_address = getattr(settings, "EMAIL_NOTIFICATION_SENDER", '"QATrack+" <notifications@qatrackplus.com>')
    fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)

    context["domain"] = Site.objects.get_current().domain

    if subject_template:
        subject = render_to_string(subject_template, context).strip()
    else:
        subject = getattr(settings, "EMAIL_NOTIFICATION_SUBJECT", "QATrack+ Notification")

    html_content = render_to_string(template, context)
    html_body = pynliner.fromString(html_content)

    if text_template:
        text_body = render_to_string(text_template, context)
    else:
        text_body = strip_tags(html_body)

    message = EmailMultiAlternatives(
        subject,
        text_body,
        from_address,
        recipients,
    )
    message.attach_alternative(html_body, "text/html")

    for name, attachment, mimetype in attachments:
        message.attach(name, attachment, mimetype)

    try:
        message.send(fail_silently=False)
    except:  # noqa: E722  # pragma: nocover
        logger.exception("Error sending email.")
        if not fail_silently:
            raise
