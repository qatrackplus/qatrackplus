from collections import defaultdict

from django.apps import apps
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
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

from qatrack.qa.models import Category, UnitTestInfo


def homepage(request):
    context = {'tree': full_tree()}
    return render(request, "homepage.html", context)


def full_tree():
    return category_tree(units_with_categories())


def units_with_categories():
    """Return dictionary of categories with the sites/units
    they're currently assigned to.  Dictionary is of form
    {category.id: [(site_name, unit_name, unit_number),...]}
    """

    unit_categories = UnitTestInfo.objects.active().order_by(
        "unit__site__name",
        "unit__name",
        "test__category__name",
    ).values_list(
        "test__category__id",
        "unit__site__name",
        "unit__name",
        "unit__number",
    ).distinct()

    cat_units = defaultdict(list)
    for unit_cat in unit_categories:
        cat_units[unit_cat[0]].append(unit_cat[1:])

    return cat_units


def category_tree(category_units):
    """
    Takes an iterable of (category.id, site.name, unit.name, unit.number,)s and
    generates a tree of QC, orgainzed by test category, available at all sites/units.
    Iterable must be sorted by (site.name, unit.name, category.name).

    Tree format is:

    [
        {
            'text': "foo",
            'nodes: [
                {
                    'text': "foo",
                    'nodes: [...],
                },
                ...
            ]
        },

        ...
    ]

    and is suitable for passing to Bootstrap Treeview
    """

    tree = [new_node("QC by Category", "tags")]
    tree_root = tree[-1]['nodes']

    for root in Category.objects.root_nodes().order_by("name"):

        # first include the parent category as it's own child so that test lists
        # containing only tests with the parent category are included
        root_nodes = get_cat_units(root, category_units, None, flatten_children=False)
        tree_root.append(new_node(root.name, "tags", True, [root_nodes]))

        # then add actual children
        for child in root.get_children():
            child_nodes = get_cat_units(child, category_units, None)
            if child_nodes['nodes']:
                tree_root[-1]['nodes'].append(child_nodes)

    return tree


def get_cat_units(parent, category_units, nodes=None, flatten_children=True):
    """collect all categories by site/unit. If flatten_children is True,
    The sites/units will not be nested another level deep, but will
    instead be appended to existing levels nodes.  This allows limiting
    to e.g. 2 levels of categories without missing units/sites.
    """

    seen_sites = set()
    seen_units = set()

    nodes = nodes or new_node(parent.name, "tag")

    if parent.id not in category_units:
        return nodes

    for site, unit, unum in category_units[parent.id]:

        if unum is None:
            continue

        if site not in seen_sites:
            seen_sites.add(site)
            seen_units = set()
            nodes['nodes'].append(new_node(site or _("No Site"), "cubes"))

        if unit not in seen_units:
            seen_units.add(unit)
            href = reverse("qa_by_unit_category", kwargs={"category": parent.slug, "unit_number": unum})
            title = _("Click to view {test_category} tests on Unit {unit}").format(test_category=parent.name, unit=unit)
            link = '<a href="%s" title="%s">%s</a>' % (href, title, unit)
            nodes['nodes'][-1]['nodes'].append(new_node(link, "cube", 1, nodes=False))

    if flatten_children:
        for child in parent.get_children():
            get_cat_units(child, category_units, nodes, flatten_children=flatten_children)

    return nodes


def new_node(text, icon, expanded=False, nodes=None):
    node = {
        'text': text + ' <i class="fa fa-%s fa-fw"></i>' % icon,
        'state': {'expanded': int(bool(expanded))},
    }
    if nodes is not False:
        node['nodes'] = nodes or []
    return node


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
