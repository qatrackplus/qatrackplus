from django.utils.safestring import mark_safe

from qatrack.attachments.templatetags.attach_tags import (
    attachment_img,
    attachment_link,
)


def listable_attachment_tags(obj, joiner=" "):
    """
    Return an html string containing links for each of the attachments for
    input object.  Images will be shown as hover images and other attachments will be
    shown as paperclip icons.
    """
    items = []
    attachments = obj.attachment_set.all()
    label = mark_safe('<i class="fa fa-paperclip fa-fw" aria-hidden="true"></i>')
    img_label = mark_safe('<i class="fa fa-photo fa-fw" aria-hidden="true"></i>')
    for a in attachments:
        if a.is_image:
            img = attachment_img(a, klass="listable-image")
            items.append(
                '<div class="hover-img"><a href="%s" target="_blank">%s<span>%s</span></a></div>' %
                (a.attachment.url, img_label, img)
            )
        else:
            items.append(attachment_link(a, label=label))

    return joiner.join(items)
