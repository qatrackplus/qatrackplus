
import re

from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import User

re_255 = '([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])'
color_re = re.compile('^rgba\(' + re_255 + ',' + re_255 + ',' + re_255 + ',(0(\.[0-9][0-9]?)?|1)\)$')
validate_color = RegexValidator(color_re, 'Enter a valid color.', 'invalid')


class IssueType(models.Model):

    name = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class IssuePriority(models.Model):

    name = models.CharField(max_length=32)
    colour = models.CharField(max_length=22, validators=[validate_color], blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Priorities'
        ordering = ['order']

    def __str__(self):
        return self.name


class IssueTag(models.Model):

    name = models.CharField(max_length=32)
    description = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class IssueStatus(models.Model):

    name = models.CharField(max_length=32)
    description = models.CharField(max_length=255, null=True, blank=True)
    colour = models.CharField(max_length=22, validators=[validate_color], blank=True, null=True)
    order = models.PositiveIntegerField(default=0, unique=True)

    class Meta:
        verbose_name_plural = 'Statuses'
        ordering = ['order']

    def __str__(self):
        return self.name


class Issue(models.Model):

    issue_type = models.ForeignKey(IssueType, on_delete=models.PROTECT)
    issue_priority = models.ForeignKey(IssuePriority, null=True, on_delete=models.PROTECT)
    issue_tags = models.ManyToManyField(IssueTag, blank=True, help_text='If desired, add multiple tags to this issue')
    issue_status = models.ForeignKey(IssueStatus, null=True, help_text='Current status of this issue')
    user_submitted_by = models.ForeignKey(User, on_delete=models.PROTECT)

    datetime_submitted = models.DateTimeField()
    description = models.TextField()
    error_screen = models.TextField(
        null=True, blank=True,
        help_text='Any error screen details. (Note the ability to click "Switch to copy-and-paste view" to copy Traceback)'
    )
