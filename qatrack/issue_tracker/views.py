
from braces.views import LoginRequiredMixin
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse, resolve
from django.forms.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django.template import Context
from django.template.loader import get_template
from django.views.generic import TemplateView, DetailView, CreateView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView

from listable.views import (
    BaseListableView, DATE_RANGE, SELECT_MULTI, NONEORNULL, TEXT, SELECT_MULTI_FROM_MULTI,
    TODAY, YESTERDAY, TOMORROW, LAST_WEEK, THIS_WEEK, NEXT_WEEK, LAST_14_DAYS, LAST_MONTH, THIS_MONTH, THIS_YEAR
)

from qatrack.issue_tracker import models as i_models
from qatrack.issue_tracker import forms as i_forms


class IssueCreate(LoginRequiredMixin, CreateView):

    model = i_models.Issue
    # form_class = AuthorForm
    template_name = 'issue_tracker/issue_form.html'
    form_class = i_forms.IssueForm

    def form_valid(self, form):

        context = self.get_context_data()

        issue = form.save(commit=False)
        issue.user_submitted_by = self.request.user
        issue.datetime_submitted = timezone.now()
        issue.issue_status = i_models.IssueStatus.objects.get(order=0)
        issue.save()
        issue.issue_tags.set(form.cleaned_data['issue_tags'])

        return HttpResponseRedirect(reverse('issue_list'))

    def get_context_data(self, **kwargs):
        context = super(IssueCreate, self).get_context_data(**kwargs)
        colours = {}
        for c in i_models.IssuePriority.objects.all():
            colours[c.id] = c.colour
        context['colours'] = colours
        tags = {}
        for t in i_models.IssueTag.objects.all():
            tags[t.id] = [t.name, t.description]
        context['tags'] = tags
        return context


class IssueDetails(LoginRequiredMixin, DetailView):

    model = i_models.Issue
    # form_class = AuthorForm
    template_name = 'issue_tracker/issue_details.html'

    def get_context_data(self, **kwargs):
        context = super(IssueDetails, self).get_context_data(**kwargs)
        context['now'] = timezone.now()
        ct = ContentType.objects.get(app_label='issue_tracker', model='issue').id
        context['ct'] = ct

        colours = {}
        for c in i_models.IssuePriority.objects.all():
            colours[c.id] = c.colour
        context['colours'] = colours

        return context


class IssueList(BaseListableView):
    model = i_models.Issue
    template_name = 'issue_tracker/issue_list.html'
    paginate_by = 50

    order_by = ['-datetime_submitted']
    kwarg_filters = None
    multi_separator = '<span class="padding-0-10">|</span>'

    fields = (
        'actions',
        'pk',
        'issue_type__name',
        'issue_priority__name',
        'user_submitted_by__username',
        'description',
        'datetime_submitted',
        'issue_tags__name',
        'issue_status__name'
    )

    headers = {
        'actions': 'Actions',
        'pk': 'ID',
        'issue_type__name': 'Type',
        'issue_priority__name': 'Priority',
        'user_submitted_by__username': 'Submitted By',
        'description': 'Description',
        'datetime_submitted': 'Submitted',
        'issue_tags__name': 'Tags',
        'issue_status__name': 'Status'
    }

    widgets = {
        'actions': None,
        'pk': TEXT,
        'issue_type__name': SELECT_MULTI,
        'issue_priority__name': SELECT_MULTI,
        'user_submitted_by__username': SELECT_MULTI,
        'description': TEXT,
        'datetime_submitted': DATE_RANGE,
        'issue_tags__name': SELECT_MULTI_FROM_MULTI,
        'issue_status__name': SELECT_MULTI
    }

    search_fields = {
        'actions': False,
    }

    order_fields = {
        'actions': False,
        'datetime_submitted': 'datetime_submitted',
        'issue_tags__name': False
    }

    date_ranges = {
        'datetime_submitted': (TODAY, YESTERDAY, LAST_WEEK, LAST_MONTH)
    }

    select_related = (
        'issue_type',
        'issue_priority',
        'user_submitted_by',
        'issue_status'
    )

    prefetch_related = (
        'issue_tags',
    )

    def get_icon(self):
        return 'fa-bug'

    def get_page_title(self, f=None):
        if not f:
            return 'All Issues'

    def get_context_data(self, *args, **kwargs):
        context = super(IssueList, self).get_context_data(*args, **kwargs)
        current_url = resolve(self.request.path_info).url_name
        context['view_name'] = current_url
        context['icon'] = self.get_icon()
        f = self.request.GET.get('f', False)
        context['kwargs'] = {'f': f} if f else {}
        context['page_title'] = self.get_page_title(f)

        return context

    def actions(self, i):
        template = get_template('issue_tracker/table_context_issue_actions.html')
        mext = reverse('issue_list')
        c = Context({'i': i, 'request': self.request, 'next': mext})
        return template.render(c)

    def datetime_submitted(self, i):
        template = get_template('service_log/table_context_datetime.html')
        c = Context({'datetime': i.datetime_submitted})
        return template.render(c)

    def issue_priority__name(self, i):
        template = get_template('issue_tracker/table_context_issue_priority.html')
        c = Context({'issue_priority': i.issue_priority, 'request': self.request})
        return template.render(c)

    def issue_status__name(self, i):
        template = get_template('issue_tracker/table_context_issue_status.html')
        c = Context({'issue_status': i.issue_status, 'request': self.request})
        return template.render(c)

    def description(self, i):
        template = get_template('issue_tracker/table_context_issue_description.html')
        c = Context({'description': i.description, 'request': self.request})
        return template.render(c)
