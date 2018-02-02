import collections
import logging

from braces.views import PrefetchRelatedMixin, SelectRelatedMixin
from django.apps import apps
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import resolve, reverse
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.views.generic import UpdateView
from django_comments import get_form
from django_comments import signals as dc_signals
from listable.views import (
    DATE_RANGE,
    LAST_14_DAYS,
    LAST_WEEK,
    NEXT_WEEK,
    NONEORNULL,
    SELECT_MULTI,
    THIS_MONTH,
    THIS_WEEK,
    THIS_YEAR,
    TODAY,
    TOMORROW,
    YESTERDAY,
    BaseListableView,
)

from qatrack.qa import models
from qatrack.service_log import models as sl_models

# signals import  needs to be here so signals get registered
from .. import signals  # NOQA

logger = logging.getLogger('qatrack.console')


def generate_review_status_context(test_list_instance):

    if not test_list_instance:
        return {}

    statuses = collections.defaultdict(lambda: {"count": 0})
    comment_count = 0
    for ti in test_list_instance.testinstance_set.all():
        statuses[ti.status.name]["count"] += 1
        statuses[ti.status.name]["valid"] = ti.status.valid
        statuses[ti.status.name]["requires_review"] = ti.status.requires_review
        statuses[ti.status.name]["reviewed_by"] = test_list_instance.reviewed_by
        statuses[ti.status.name]["reviewed"] = test_list_instance.reviewed
        if ti.comment:
            comment_count += 1
    comment_count += test_list_instance.comments.all().count()

    c = {
        "statuses": dict(statuses),
        "comments": comment_count,
        "show_icons": settings.ICON_SETTINGS['SHOW_REVIEW_ICONS']
    }

    return c


class TestListInstanceMixin(SelectRelatedMixin, PrefetchRelatedMixin):
    """
    A mixin for commonly required prefetch_related/select_related  for
    :model:`qa.TestListInstance` views
    """

    model = models.TestListInstance
    context_object_name = "test_list_instance"

    prefetch_related = [
        "testinstance_set__unit_test_info",
        "testinstance_set__unit_test_info__test",
        "testinstance_set__reference",
        "testinstance_set__tolerance",
        "testinstance_set__status",
    ]
    select_related = [
        "unit_test_collection",
        "unit_test_collection__unit",
        "created_by",
        "modified_by",
        "test_list",
    ]


class BaseEditTestListInstance(TestListInstanceMixin, UpdateView):
    """A common base for editing existing :model:`qa.TestListInstance`'s"""

    def add_histories(self, forms):
        """paste historical values onto forms"""

        history, history_dates = self.object.history()
        self.history_dates = history_dates
        for f in forms:
            for instance, test_history in history:
                if f.instance == instance:
                    f.history = test_history

    def get_context_data(self, **kwargs):

        context = super(BaseEditTestListInstance, self).get_context_data(**kwargs)

        # override the default queryset for the formset so that we can pull in all the
        # reference/tolerance data without the ORM generating lots of extra queries
        test_instances = self.object.testinstance_set.order_by("created").select_related(
            "status",
            "reference",
            "tolerance",
            "unit_test_info__test",
            "unit_test_info__test__category",
            "unit_test_info__unit",
        ).prefetch_related(
            "unit_test_info__test__attachment_set",
        )

        if self.request.method == "POST":
            formset = self.formset_class(
                self.request.POST,
                self.request.FILES,
                instance=self.object,
                queryset=test_instances,
                user=self.request.user
            )
        else:
            formset = self.formset_class(instance=self.object, queryset=test_instances, user=self.request.user)

        self.add_histories(formset.forms)
        context["formset"] = formset
        context["history_dates"] = self.history_dates
        context["categories"] = set([x.unit_test_info.test.category for x in test_instances])
        context["statuses"] = models.TestInstanceStatus.objects.all()
        context["test_list"] = self.object.test_list
        context["unit_test_collection"] = self.object.unit_test_collection
        context["current_day"] = self.object.day + 1

        tests = [t.unit_test_info.test for t in test_instances]
        context['borders'] = self.object.test_list.sublist_borders(tests)

        context['attachments'] = self.object.unit_test_collection.tests_object.attachment_set.all()

        rtsqas = sl_models.ReturnToServiceQA.objects.filter(test_list_instance=self.object)
        se_rtsqa = []
        for f in rtsqas:
            if f.service_event not in se_rtsqa:
                se_rtsqa.append(f.service_event)

        context['service_events_rtsqa'] = se_rtsqa

        se_ib = sl_models.ServiceEvent.objects.filter(test_list_instance_initiated_by=self.object)
        context['service_events_ib'] = se_ib

        return context

    def form_valid(self, form):
        """This view should always be subclassed"""
        raise NotImplementedError

    def get_success_url(self):
        next_ = self.request.GET.get("next", None)
        if next_ is not None:
            return next_

        return reverse("unreviewed")


class UTCList(BaseListableView):

    model = models.UnitTestCollection

    action = "perform"
    action_display = "Perform"
    page_title = "All QA"
    active_only = True
    inactive_only = False
    visible_only = True
    paginate_by = 50

    fields = (
        "actions",
        "name",
        "due_date",
        "unit__name",
        "frequency__name",
        "assigned_to__name",
        "last_instance__work_completed",
        "last_instance_pass_fail",
        "last_instance_review_status",
    )

    search_fields = {
        "actions": False,
        "name": "name",
        "assigned_to__name": "assigned_to__name",
        "last_instance_pass_fail": False,
        "last_instance_review_status": False,
    }

    order_fields = {
        "actions": False,
        "frequency__name": "frequency__due_interval",
        "unit__name": "unit__number",
        "last_instance_pass_fail": False,
        "last_instance_review_status": False,
        "due_date": "due_date"
    }

    widgets = {
        "unit__name": SELECT_MULTI,
        "frequency__name": SELECT_MULTI,
        "assigned_to__name": SELECT_MULTI,
        "last_instance__work_completed": DATE_RANGE,
        "due_date": DATE_RANGE
    }

    date_ranges = {
        "last_instance__work_completed": [TODAY, YESTERDAY, THIS_WEEK, LAST_14_DAYS, THIS_MONTH, THIS_YEAR],
        "due_date": [YESTERDAY, TODAY, TOMORROW, LAST_WEEK, THIS_WEEK, NEXT_WEEK]
    }

    select_related = (
        "last_instance",
        "frequency",
        "unit",
        "assigned_to",
    )

    headers = {
        "name": _("Test List/Cycle"),
        "unit__name": _("Unit"),
        "frequency__name": _("Frequency"),
        "assigned_to__name": _("Assigned To"),
        "last_instance__work_completed": _("Completed"),
        "last_instance_pass_fail": _("Pass/Fail Status"),
        "last_instance_review_status": _("Review Status"),
    }

    prefetch_related = (
        'last_instance__testinstance_set',
        'last_instance__testinstance_set__status',
        'last_instance__reviewed_by',
        'last_instance__modified_by',
        'last_instance__created_by',
        'last_instance__comments',
    )

    order_by = ["unit__name", "frequency__name", "name"]

    def __init__(self, *args, **kwargs):
        super(UTCList, self).__init__(*args, **kwargs)

        if self.active_only and self.inactive_only:
            raise ValueError(
                "Misconfigured View: %s. active_only and  inactive_only can't both be True" % self.__class__
            )

        # Store templates on view initialization so we don't have to reload them for every row!
        self.templates = {
            'actions': get_template("qa/unittestcollection_actions.html"),
            'work_completed': get_template("qa/testlistinstance_work_completed.html"),
            'review_status': get_template("qa/testlistinstance_review_status.html"),
            'pass_fail': get_template("qa/pass_fail_status.html"),
            'due_date': get_template("qa/due_date.html"),
        }

    def get_icon(self):
        return 'fa-pencil-square-o'

    def get_context_data(self, *args, **kwargs):
        context = super(UTCList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['action'] = self.action
        context['page_title'] = self.get_page_title()
        context['icon'] = self.get_icon()

        return context

    def get_page_title(self):
        return self.page_title

    def get_queryset(self):
        """filter queryset for visibility and fetch relevent related objects"""

        qs = super(UTCList, self).get_queryset()

        if self.visible_only:
            qs = qs.filter(visible_to__in=self.request.user.groups.all(),).distinct()

        if self.active_only:
            qs = qs.filter(active=True, unit__active=True)

        if self.inactive_only:
            qs = qs.filter(Q(active=False) | Q(unit__active=False))

        return qs

    def get_filters(self, field, queryset=None):

        filters = super(UTCList, self).get_filters(field, queryset=queryset)

        if field == 'frequency__name':
            filters = [(NONEORNULL, 'Ad Hoc') if f == (NONEORNULL, 'None') else f for f in filters]

        return filters

    def frequency__name(self, utc):
        return utc.frequency.name if utc.frequency else 'Ad Hoc'

    def actions(self, utc):
        template = self.templates['actions']
        perms = PermWrapper(self.request.user)
        c = {'utc': utc, 'request': self.request, 'action': self.action, 'perms': perms}
        return template.render(c)

    def due_date(self, utc):
        template = self.templates['due_date']
        c = {'unit_test_collection': utc, 'show_icons': settings.ICON_SETTINGS['SHOW_DUE_ICONS']}
        return template.render(c)

    def last_instance__work_completed(self, utc):
        template = self.templates['work_completed']
        c = {"instance": utc.last_instance}
        return template.render(c)

    def last_instance_review_status(self, utc):
        template = self.templates['review_status']
        c = {'instance': utc.last_instance, 'perms': PermWrapper(self.request.user), 'request': self.request}
        c.update(generate_review_status_context(utc.last_instance))
        return template.render(c)

    def last_instance_pass_fail(self, utc):
        template = self.templates['pass_fail']
        c = {
            'instance': utc.last_instance,
            'exclude': [models.NO_TOL],
            'show_label': settings.ICON_SETTINGS['SHOW_STATUS_LABELS_LISTING'],
            'show_icons': settings.ICON_SETTINGS['SHOW_STATUS_ICONS_LISTING']
        }
        return template.render(c)


class TestListInstances(BaseListableView):
    """
    This view provides a base for any sort of listing of
    :model:`qa.TestListInstance`'s.
    """

    model = models.TestListInstance
    paginate_by = 50

    order_by = ["unit_test_collection__unit__name", "-work_completed"]

    fields = (
        "actions",
        "unit_test_collection__unit__name",
        "unit_test_collection__frequency__name",
        "test_list__name",
        "work_completed",
        "created_by__username",
        "review_status",
        "pass_fail",
    )

    headers = {
        "unit_test_collection__unit__name": _("Unit"),
        "unit_test_collection__frequency__name": _("Frequency"),
        "created_by__username": _("Created By"),
    }

    widgets = {
        "unit_test_collection__frequency__name": SELECT_MULTI,
        "unit_test_collection__unit__name": SELECT_MULTI,
        "created_by__username": SELECT_MULTI,
        "work_completed": DATE_RANGE
    }

    date_ranges = {"work_completed": [TODAY, YESTERDAY, THIS_WEEK, LAST_14_DAYS, THIS_MONTH, THIS_YEAR]}

    search_fields = {
        "actions": False,
        "pass_fail": False,
        "review_status": False,
    }

    order_fields = {
        "actions": False,
        "unit_test_collection__unit__name": "unit_test_collection__unit__number",
        "unit_test_collection__frequency__name": "unit_test_collection__frequency__due_interval",
        "review_status": False,
        "pass_fail": False,
    }

    select_related = (
        "test_list",
        "unit_test_collection__unit",
        "unit_test_collection__frequency",
        "created_by",
        "modified_by",
        "reviewed_by",
    )

    prefetch_related = (
        'testinstance_set',
        'testinstance_set__status',
        'rtsqa_for_tli',
        'rtsqa_for_tli__service_event',
        'serviceevents_initiated',
        'comments',
    )

    def __init__(self, *args, **kwargs):
        super(TestListInstances, self).__init__(*args, **kwargs)

        self.templates = {
            'actions': get_template("qa/testlistinstance_actions.html"),
            'work_completed': get_template("qa/testlistinstance_work_completed.html"),
            'review_status': get_template("qa/testlistinstance_review_status.html"),
            'pass_fail': get_template("qa/pass_fail_status.html"),
        }

    def get_icon(self):
        return 'fa-question-circle'

    def get_page_title(self):
        return "All Test Collections"

    def get_context_data(self, *args, **kwargs):
        context = super(TestListInstances, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        context["page_title"] = self.get_page_title()
        return context

    def get_filters(self, field, queryset=None):

        filters = super(TestListInstances, self).get_filters(field, queryset=queryset)

        if field == 'unit_test_collection__frequency__name':
            filters = [(NONEORNULL, 'Ad Hoc') if f == (NONEORNULL, 'None') else f for f in filters]

        return filters

    def unit_test_collection__frequency__name(self, tli):
        freq = tli.unit_test_collection.frequency
        return freq.name if freq else "Ad Hoc"

    def actions(self, tli):
        template = self.templates['actions']

        rtsqas = tli.rtsqa_for_tli.all()
        se_rtsqa = []
        for f in rtsqas:
            if f.service_event not in se_rtsqa:
                se_rtsqa.append(f.service_event)

        se_ib = tli.serviceevents_initiated.all()

        c = {
            'instance': tli,
            'perms': PermWrapper(self.request.user),
            'request': self.request,
            'show_initiate_se': True,
            'initiated_se': se_ib,
            'num_initiated_se': len(se_ib),
            'show_rtsqa_se': True,
            'rtsqa_for_se': se_rtsqa,
            'num_rtsqa_se': len(se_rtsqa)
        }
        return template.render(c)

    def work_completed(self, tli):
        template = self.templates['work_completed']
        return template.render({"instance": tli})

    def review_status(self, tli):
        template = self.templates['review_status']
        c = {
            "instance": tli,
            "perms": PermWrapper(self.request.user),
            "request": self.request,
            "show_label": settings.ICON_SETTINGS['SHOW_REVIEW_LABELS_LISTING'],
            "show_icons": settings.ICON_SETTINGS['SHOW_STATUS_ICONS_REVIEW']
        }
        c.update(generate_review_status_context(tli))
        return template.render(c)

    def pass_fail(self, tli):
        template = self.templates['pass_fail']
        c = {
            "instance": tli,
            "exclude": [models.NO_TOL],
            "show_label": settings.ICON_SETTINGS['SHOW_REVIEW_LABELS_LISTING'],
            "show_icons": settings.ICON_SETTINGS['SHOW_STATUS_ICONS_LISTING']
        }
        return template.render(c)


@require_POST
@csrf_protect
def ajax_comment(request, next=None, using=None):
    """
    Post a comment.

    Copied from django_comment comments.py > post_comment method. Adjusted for ajax response
    """
    # Fill out some initial data fields from an authenticated user, if present
    data = request.POST.copy()

    try:
        user_is_authenticated = request.user.is_authenticated()
    except TypeError:  # Django >= 1.11
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
        return JsonResponse({'error': True, 'message': 'Missing content_type or object_pk field.'}, status=500)
    try:
        model = apps.get_model(*ctype.split(".", 1))
        target = model._default_manager.using(using).get(pk=object_pk)
    except TypeError:
        return JsonResponse({'error': True, 'message': 'Invalid content_type value: %r' % escape(ctype)}, status=500)
    except AttributeError:
        return JsonResponse(
            {
                'error': True,
                'message': 'The given content-type %r does not resolve to a valid model.' % escape(ctype)
            },
            status=500,
        )
    except ObjectDoesNotExist:
        return JsonResponse(
            {
                'error':
                    True,
                'message':
                    'No object matching content-type %r and object PK %r exists.' % (escape(ctype), escape(object_pk))
            },
            status=500,
        )
    except (ValueError, ValidationError) as e:
        return JsonResponse(
            {
                'error':
                    True,
                'message':
                    'Attempting go get content-type %r and object PK %r exists raised %s' %
                    (escape(ctype), escape(object_pk), e.__class__.__name__)
            },
            status=500,
        )

    # Do we want to preview the comment?
    preview = "preview" in data

    # Construct the comment form
    form = get_form()(target, data=data)

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
    if form.errors or preview:
        template_list = [
            # These first two exist for purely historical reasons.
            # Django v1.0 and v1.1 allowed the underscore format for
            # preview templates, so we have to preserve that format.
            "comments/%s_%s_preview.html" % (model._meta.app_label, model._meta.model_name),
            "comments/%s_preview.html" % model._meta.app_label,
            # Now the usual directory based template hierarchy.
            "comments/%s/%s/preview.html" % (model._meta.app_label, model._meta.model_name),
            "comments/%s/preview.html" % model._meta.app_label,
            "comments/preview.html",
        ]
        return render(
            request, template_list, {
                "comment": form.data.get("comment", ""),
                "form": form,
                "next": data.get("next", next),
            }
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
                    'message': 'comment_will_be_posted receiver %r killed the comment' % receiver.__name__
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
    })
