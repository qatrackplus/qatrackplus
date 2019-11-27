from django.apps import apps
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Case, CharField, F, Value, When
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

from qatrack.qa.models import Category, UnitTestCollection


def homepage(request):
    context = {
        'freq_tree': frequency_tree(request.user.groups.all()),
        'cat_tree': category_tree(request.user.groups.all()),
    }
    return render(request, "homepage.html", context)


def category_tree(groups):

    root_cats = dict(Category.objects.root_nodes().values_list("tree_id", "name"))
    cats = {}
    for cat in Category.objects.order_by("tree_id", "level", "name"):
        cats[cat.name] = cat.tree_id

    utcs = UnitTestCollection.objects.filter(
        unit__active=True,
        active=True,
        visible_to__in=groups,
    ).annotate(
        cat_tree_id=Case(
            When(
                test_list__testlistmembership__test__category__tree_id__isnull=False,
                then=F("test_list__testlistmembership__test__category__tree_id")
            ),
            When(
                test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,
                then=F("test_list__children__child__testlistmembership__test__category__tree_id")
            ),
            When(
                test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                then=F("test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__tree_id")  # noqa: E501
            ),
            When(
                test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                then=F(
                    "test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__tree_id"  # noqa: E501
                )
            ),
            default=Value(""),
            output_field=CharField(),
        ),
        cat_name=Case(
            When(
                test_list__testlistmembership__test__category__tree_id__isnull=False,
                then=F("test_list__testlistmembership__test__category__name")
            ),
            When(
                test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,
                then=F("test_list__children__child__testlistmembership__test__category__name")
            ),
            When(
                test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                then=F("test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__name")  # noqa: E501
            ),
            When(
                test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                then=F(
                    "test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__name"  # noqa: E501
                )
            ),
            default=Value(""),
            output_field=CharField(),
        )
    ).order_by(
        "unit__site__name",
        "unit__%s" % settings.ORDER_UNITS_BY,
        "frequency__nominal_interval",
        "cat_tree_id",
        "cat_name",
        "name",
    ).values_list(
        "id",
        "name",
        "unit__site__name",
        "unit__number",
        "unit__name",
        "frequency__name",
        "cat_tree_id",
        "cat_name",
    ).distinct()  # yapf: disable

    seen_sites = set()

    tree = [new_node(_("QC by Unit, Frequency, & Category"), "")]
    root_nodes = tree[-1]['nodes']

    for utc_id, utc_name, site, unum, uname, freq_name, cat_tree_id, cat_name in utcs:

        if not freq_name:
            freq_name = _("Ad-Hoc")

        if site not in seen_sites:
            seen_sites.add(site)
            seen_units = set()
            root_nodes.append(new_node(site or _("No Site"), "cubes"))
            site_nodes = root_nodes[-1]['nodes']

        if unum not in seen_units:
            seen_units.add(unum)
            seen_freqs = set()
            site_nodes.append(new_node(uname, "cube", 0))
            unit_nodes = site_nodes[-1]['nodes']

        if freq_name not in seen_freqs:
            seen_freqs.add(freq_name)
            seen_roots = set()
            unit_nodes.append(new_node(freq_name, "clock-o", 0))
            freq_nodes = unit_nodes[-1]['nodes']

        if cat_tree_id not in seen_roots:
            seen_roots.add(cat_tree_id)
            seen_names = set()
            freq_nodes.append(new_node(root_cats[cat_tree_id], "tag", 1))
            cat_nodes = freq_nodes[-1]['nodes']

        if utc_name not in seen_names:
            seen_names.add(utc_name)
            href = reverse("perform_qa", kwargs={"pk": utc_id})
            title = _("Click to peform {tests_collection} on Unit {unit}").format(tests_collection=utc_name, unit=uname)
            link = '<a href="%s" title="%s">%s</a>' % (href, title, utc_name)
            cat_nodes.append(new_node(link, "list", 1, nodes=False))

    return tree


def frequency_tree(groups):

    utcs = UnitTestCollection.objects.filter(
        visible_to__in=groups,
        unit__active=True,
        active=True,
    ).order_by(
        "unit__site__name",
        "unit__%s" % settings.ORDER_UNITS_BY,
        "frequency__nominal_interval",
        "name",
    ).values_list(
        "id",
        "name",
        "frequency__slug",
        "frequency__name",
        "unit__site__name",
        "unit__number",
        "unit__name",
    )

    seen_freqs = set()
    seen_sites = set()
    seen_units = set()
    seen_names = set()

    tree = [new_node(_("QC by Unit & Frequency"), "cubes")]
    root_nodes = tree[-1]['nodes']

    for utc_id, utc_name, fslug, fname, site, unum, uname in utcs:

        if not fslug:
            fslug = "ad-hoc"
            fname = _("Ad-Hoc")

        if site not in seen_sites:
            seen_sites.add(site)
            seen_units = set()
            root_nodes.append(new_node(site or _("No Site"), "cubes"))
            site_nodes = root_nodes[-1]['nodes']

        if unum not in seen_units:
            seen_units.add(unum)
            seen_freqs = set()
            site_nodes.append(new_node(uname, "cube", 0))
            unit_nodes = site_nodes[-1]['nodes']

        if fname not in seen_freqs:
            seen_freqs.add(fname)
            seen_names = set()
            unit_nodes.append(new_node(fname, "clock-o"))
            freq_nodes = unit_nodes[-1]['nodes']

        if utc_name not in seen_names:
            seen_names.add(utc_name)
            href = reverse("perform_qa", kwargs={"pk": utc_id})
            title = _("Click to peform {tests_collection} on Unit {unit}").format(tests_collection=utc_name, unit=uname)
            link = '<a href="%s" title="%s">%s</a>' % (href, title, utc_name)
            freq_nodes.append(new_node(link, "list", 1, nodes=False))

    return tree


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
