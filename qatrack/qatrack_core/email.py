import logging
from io import BytesIO

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import pynliner

logger = logging.getLogger('qatrack')


def email_context(context):
    context = context or {}
    site = Site.objects.get_current()
    domain = site.domain
    if not domain.startswith("http"):
        domain = "%s://%s" % (settings.HTTP_OR_HTTPS, domain)
    context.update({
        "domain": domain,
        "site_obj": site,
    })
    return context


def send_email_to_users(
    recipients, template, context=None, subject_template=None, text_template=None, attachments=None
):

    if len(recipients) == 0:
        return

    attachments = attachments or []

    context = email_context(context)

    from_address = getattr(settings, "EMAIL_NOTIFICATION_SENDER", '"QATrack+" <notifications@qatrackplus.com>')
    fail_silently = getattr(settings, "EMAIL_FAIL_SILENTLY", True)

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
        if isinstance(attachment, BytesIO):
            attachment.seek(0)
            attachment = attachment.read()
        message.attach(name, attachment, mimetype)

    try:
        message.send(fail_silently=False)
    except Exception:  # noqa: E722  # pragma: nocover
        logger.exception("Error sending email.")
        if not fail_silently:
            raise
