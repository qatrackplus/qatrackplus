from collections import defaultdict

from django.apps import apps
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django_comments import signals as dc_signals
from django_comments.forms import CommentForm

from qatrack.qa.models import Category, UnitTestCollection, UnitTestInfo


def homepage(request):

    context = {'tree': category_tree()}
    return render(request, "homepage.html", context)


def category_tree():

    cat_units = defaultdict(list)
    vals = UnitTestInfo.objects.order_by(
        "unit__site__name",
        "unit__name",
        "test__category__name",
    ).values_list(
        "test__category__id",
        "unit__site__name",
        "unit__name",
        "unit__number",
    )
    for val in vals:
        cat_units[val[0]].append(val[1:])

    tree = [{
        'text': 'QC By Category <i class="fa fa-tags fa-fw"></i>',
        'nodes': [],
        'state': {
            'expanded': 0
        },
    }]

    tree_root = tree[-1]['nodes']

    roots = Category.objects.root_nodes().order_by("name")

    for root in roots:
        root_nodes = []

        if root.is_leaf_node():
            root_nodes = get_cat_units(root, cat_units, None)
            if root_nodes['nodes']:
                tree_root.append(root_nodes)
        else:
            root_nodes = get_cat_units(root, cat_units, None, children=False)
            tree_root.append({
                'text': '%s <i class="fa fa-tags fa-fw"></i>' % root.name,
                'nodes': [root_nodes],
                'state': {
                    'expanded': 1
                },
            })
            for child in root.get_children():
                child_nodes = get_cat_units(child, cat_units, None)
                if child_nodes['nodes']:
                    tree_root[-1]['nodes'].append(child_nodes)
                    tree_root[-1]['state'] = {'expanded': 1}

    return tree


def get_cat_units(parent, qs, nodes=None, children=True):

    seen_sites = set()
    seen_units = set()


    if nodes is None:
        href = reverse("qa_by_category", kwargs={"category": parent.slug})
        title = _("Click to view {test_category} tests on all units").format(test_category=parent.name)
        link = '<a href="%s" title="%s">%s <i class="fa fa-tag fa-fw"></i></a>' % (href, title, parent.name)
        nodes = {'text': link, 'nodes': []}

    href_template = reverse("qa_by_unit_category", kwargs={"category": parent.slug, "unit_number": 0xC0DEC0DE})
    unum_replace = str(0xC0DEC0DE)

    for site, unit, unum in qs[parent.id]:

        if unum is None:
            continue

        if site not in seen_sites:
            seen_sites.add(site)
            seen_units = set()
            nodes['nodes'].append({
                'text': '%s <i class="fa fa-cubes fa-fw"></i>' % (site or _("No Site")),
                'nodes': [],
            })

        if unit not in seen_units:
            seen_units.add(unit)
            href = href_template.replace(unum_replace, str(unum))
            title = _("Click to view {test_category} tests on Unit {unit}").format(test_category=parent.name, unit= unit)
            link = '<a href="%s" title="%s">%s <i class="fa fa-cube fa-fw"></i></a>' % (href, title, unit)
            nodes['nodes'][-1]['nodes'].append({'text': link})

    if children:
        for child in parent.get_children():
            get_cat_units(child, qs, nodes)

    return nodes


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
