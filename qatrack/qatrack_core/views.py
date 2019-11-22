from collections import OrderedDict, defaultdict
import json

from django.apps import apps
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django_comments import signals as dc_signals
from django_comments.forms import CommentForm

from qatrack.qa.models import Category, UnitTestCollection
from qatrack.units.models import Site, Unit


def homepage(request):

    categories = Category.objects.all()
    sites = Site.objects.prefetch_related("unit_set")
    units = Unit.objects.select_related("site").order_by(F("site__name").asc(nulls_last=True))
    utcs = UnitTestCollection.objects.by_visibility(request.user.groups.all())
    context = {
        'categories': categories,
        'sites': sites,
        'units': units,
        'site_tree': json.dumps(list(site_tree(utcs).values())),
    }
    return render(request, "homepage.html", context)



def site_tree(utcs):
    unit_cats = utcs.values_list(
        "unit__site__name",
        "unit_id",
        "unit__name",
        "test_list__testlistmembership__test__category__slug",
        "test_list__testlistmembership__test__category__name",
        "test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__slug",
        "test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__name",
    )
    tree = {}

    for uid, un, sn, tls, tln, tlcs, tlcn in unit_cats:
        if sn not in tree:
            tree[sn] = {'text': sn, 'nodes': OrderedDict()}

        if uid not in tree[sn]['nodes']:
            tree[sn]['nodes'][uid] = {'text': un, 'nodes': []}

        cat = (tls, tln) if tls else (tlcs, tlcn)
        tree[sn]['nodes'][uid]['nodes'] = {'text': cat}


    return tree






class CustomCommentForm(CommentForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = False


@require_POST
@csrf_protect
def ajax_comment(request, next=None, using=None):
    """
    Post a comment.

    Copied from django_comment comments.py > post_comment method. Adjusted for ajax response
    """
    # Fill out some initial data fields from an authenticated user, if present
    data = request.POST.copy()

    user_is_authenticated = request.user.is_authenticated
    if user_is_authenticated:
        if not data.get('name', ''):
            data["name"] = request.user.get_full_name() or request.user.get_username()
        if not data.get('email', ''):
            data["email"] = request.user.email

    # Look up the object we're trying to comment about
    ctype = data.get("content_type")
    object_pk = data.get("object_pk")
    if ctype is None or object_pk is None:
        return JsonResponse({'error': True, 'message': _('Missing content_type or object_pk field.')}, status=500)
    try:
        model = apps.get_model(*ctype.split(".", 1))
        target = model._default_manager.using(using).get(pk=object_pk)
    except TypeError:
        return JsonResponse({
            'error': True,
            'message': _('Invalid content_type value: %(content_type)r') % {
                'content_type': escape(ctype)
            }
        }, status=500)
    except AttributeError:
        return JsonResponse(
            {
                'error': True,
                'message':
                    _('The given content-type %(content_type)r does not resolve to a valid model.') % {
                        'content_type': escape(ctype)
                    }
            },
            status=500,
        )
    except ObjectDoesNotExist:
        return JsonResponse(
            {
                'error': True,
                'message': _('No object matching content-type %(content_type)r and object PK %(object_id)r exists.') % {
                    'content_type': escape(ctype),
                    'object_id': escape(object_pk)
                },
            },
            status=500,
        )
    except (ValueError, ValidationError) as e:
        return JsonResponse(
            {
                'error': True,
                'message': _(
                    'Attempting to get content-type %(content_type)r and '
                    'object PK %(object_id)r exists raised %(error_class)s'
                ) % {
                    'content_type': escape(ctype),
                    'object_id': escape(object_pk),
                    'error_class': e.__class__.__name__,
                }
            },
            status=500,
        )

    # Do we want to preview the comment?
    # preview = "preview" in data

    # Construct the comment form
    form = CustomCommentForm(target, data=data)

    # Check security information
    if form.security_errors():
        return JsonResponse(
            {
                'error': True,
                'message': 'The comment form failed security verification: %s' % escape(str(form.security_errors()))
            },
            status=500,
        )

    # If there are errors or if we requested a preview show the comment
    if form.errors:
        return JsonResponse(
            {
                'error': True,
                'message': _('The comment submission failed'),
                'extra': form.errors
            },
            status=400,
        )

    # Otherwise create the comment
    comment = form.get_comment_object(site_id=get_current_site(request).id)
    comment.ip_address = request.META.get("REMOTE_ADDR", None)
    if user_is_authenticated:
        comment.user = request.user

    # Signal that the comment is about to be saved
    responses = dc_signals.comment_will_be_posted.send(
        sender=comment.__class__,
        comment=comment,
        request=request,
    )

    for (receiver, response) in responses:
        if response is False:
            return JsonResponse(
                {
                    'error': True,
                    'message': _('comment_will_be_posted receiver %(receiver_name)r killed the comment') % {
                        'receiver_name': receiver.__name__,
                    },
                },
                status=500,
            )

    edit_tli = 'edit-tli' in data and data['edit-tli'] == 'edit-tli'
    # Save the comment and signal that it was saved
    comment.save()
    dc_signals.comment_was_posted.send(
        sender=comment.__class__,
        comment=comment,
        request=request,
        edit_tli=edit_tli,
    )

    return JsonResponse({
        'success': True,
        'comment': comment.comment,
        'c_id': comment.id,
        'user_name': comment.user.get_full_name(),
        'submit_date': comment.submit_date,
        'template': render_to_string('comments/comment.html', {'comment': comment, 'hidden': True})
    })


def handle_error(request, code, type_, message, exception=None):
    context = {
        'code': code,
        'type': type_,
        'message': message,
    }
    return render(request, 'site_error.html', context, status=code)


def handle_400(request, exception=None):
    return handle_error(request, 400, _("Bad Request"), _("Please check your ALLOWED_HOST setting."), exception)


def handle_403(request, exception=None):
    return handle_error(
        request,
        403,
        _("Insufficient Permission"),
        _("Please talk to an administrator to acquire the required permission."),
        exception,
    )


def handle_404(request, exception=None):
    return handle_error(
        request,
        404,
        _("Resource not found"),
        _("The page or resource you were looking for can not be found"),
        exception,
    )


def handle_500(request, exception=None):
    return handle_error(
        request,
        500,
        _("Server Error"),
        _("Sorry, the server experienced an error processing your request. The site admin has been notified "),
        exception,
    )
