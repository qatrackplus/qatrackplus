# -*- coding: utf-8 -*-


from django.db import migrations, models
import django.utils.timezone
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0006_require_contenttypes_0002'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('units', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoReviewRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pass_fail', models.CharField(unique=True, max_length=15, choices=[(b'not_done', b'Not Done'), (b'ok', b'OK'), (b'tolerance', b'Tolerance'), (b'action', b'Action'), (b'no_tol', b'No Tol Set')])),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('slug', models.SlugField(help_text='Unique identifier made of lowercase characters and underscores', unique=True, max_length=255)),
                ('description', models.TextField(help_text='Give a brief description of what type of tests should be included in this grouping')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name_plural': 'categories',
            },
        ),
        migrations.CreateModel(
            name='Frequency',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Display name for this frequency', unique=True, max_length=50)),
                ('slug', models.SlugField(help_text='Unique identifier made of lowercase characters and underscores for this frequency', unique=True)),
                ('nominal_interval', models.PositiveIntegerField(help_text='Nominal number of days between test completions')),
                ('due_interval', models.PositiveIntegerField(help_text='How many days since last completed until a test with this frequency is shown as due')),
                ('overdue_interval', models.PositiveIntegerField(help_text='How many days since last completed until a test with this frequency is shown as over due')),
            ],
            options={
                'ordering': ('nominal_interval',),
                'verbose_name_plural': 'frequencies',
                'permissions': (('can_choose_frequency', 'Choose QA by Frequency'),),
            },
        ),
        migrations.CreateModel(
            name='Reference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Enter a short name for this reference', max_length=255)),
                ('type', models.CharField(default=b'numerical', max_length=15, choices=[(b'numerical', b'Numerical'), (b'boolean', b'Yes / No')])),
                ('value', models.FloatField(help_text='Enter the reference value for this test.')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(related_name='reference_creators', editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(related_name='reference_modifiers', editable=False, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Name for this test', unique=True, max_length=255, db_index=True)),
                ('slug', models.SlugField(help_text='A short variable name consisting of alphanumeric characters and underscores for this test (to be used in composite calculations). ', max_length=128, verbose_name=b'Macro name')),
                ('description', models.TextField(help_text='A concise description of what this test is for (optional. You may use HTML markup)', null=True, blank=True)),
                ('procedure', models.CharField(help_text='Link to document describing how to perform this test', max_length=512, null=True, blank=True)),
                ('chart_visibility', models.BooleanField(default=True, verbose_name=b'Test item visible in charts?')),
                ('auto_review', models.BooleanField(default=False, verbose_name='Allow auto review of this test?')),
                ('type', models.CharField(default=b'simple', help_text='Indicate if this test is a Boolean,Simple Numerical,Multiple Choice,Constant,Composite,String,String Composite,File Upload', max_length=10, choices=[(b'boolean', b'Boolean'), (b'simple', b'Simple Numerical'), (b'multchoice', b'Multiple Choice'), (b'constant', b'Constant'), (b'composite', b'Composite'), (b'string', b'String'), (b'scomposite', b'String Composite'), (b'upload', b'File Upload')])),
                ('hidden', models.BooleanField(default=False, help_text="Don't display this test when performing QA", verbose_name='Hidden')),
                ('skip_without_comment', models.BooleanField(default=False, help_text='Allow users to skip this test without a comment', verbose_name='Skip without comment')),
                ('display_image', models.BooleanField(default=False, help_text='Image uploads only: Show uploaded images under the testlist', verbose_name=b'Display image')),
                ('choices', models.CharField(help_text='Comma seperated list of choices for multiple choice test types', max_length=2048, null=True, blank=True)),
                ('constant_value', models.FloatField(help_text='Only required for constant value types', null=True, blank=True)),
                ('calculation_procedure', models.TextField(help_text='For Composite Tests Only: Enter a Python snippet for evaluation of this test.', null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(help_text='Choose a category for this test', to='qa.Category')),
                ('created_by', models.ForeignKey(related_name='test_creator', editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(related_name='test_modifier', editable=False, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TestInstance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('review_date', models.DateTimeField(null=True, editable=False, blank=True)),
                ('pass_fail', models.CharField(db_index=True, max_length=20, editable=False, choices=[(b'not_done', b'Not Done'), (b'ok', b'OK'), (b'tolerance', b'Tolerance'), (b'action', b'Action'), (b'no_tol', b'No Tol Set')])),
                ('value', models.FloatField(help_text='For boolean Tests a value of 0 equals False and any non zero equals True', null=True)),
                ('string_value', models.CharField(max_length=1024, null=True, blank=True)),
                ('skipped', models.BooleanField(default=False, help_text='Was this test skipped for some reason (add comment)')),
                ('comment', models.TextField(help_text='Add a comment to this test', null=True, blank=True)),
                ('work_started', models.DateTimeField(editable=False, db_index=True)),
                ('work_completed', models.DateTimeField(default=django.utils.timezone.now, help_text=b'Format DD-MM-YY hh:mm (hh:mm is 24h time e.g. 31-05-12 14:30)', db_index=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(related_name='test_instance_creator', editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(related_name='test_instance_modifier', editable=False, to=settings.AUTH_USER_MODEL)),
                ('reference', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to='qa.Reference', null=True)),
                ('reviewed_by', models.ForeignKey(blank=True, editable=False, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'get_latest_by': 'work_completed',
                'permissions': (('can_view_history', 'Can see test history when performing QA'), ('can_view_charts', 'Can view charts of test history'), ('can_review', 'Can review & approve tests'), ('can_skip_without_comment', 'Can skip tests without comment'), ('can_review_own_tests', 'Can review & approve  self-performed tests')),
            },
        ),
        migrations.CreateModel(
            name='TestInstanceStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Display name for this status type', unique=True, max_length=50)),
                ('slug', models.SlugField(help_text='Unique identifier made of lowercase characters and underscores for this status', unique=True)),
                ('description', models.TextField(help_text='Give a brief description of what type of test results should be given this status', null=True, blank=True)),
                ('is_default', models.BooleanField(default=False, help_text='Check to make this status the default for new Test Instances')),
                ('requires_review', models.BooleanField(default=True, help_text='Check to indicate that Test Instances with this status require further review')),
                ('export_by_default', models.BooleanField(default=True, help_text='Check to indicate whether tests with this status should be exported by default (e.g. for graphing/control charts)')),
                ('valid', models.BooleanField(default=True, help_text='If unchecked, data with this status will not be exported and the TestInstance will not be considered a valid completed Test')),
            ],
            options={
                'verbose_name_plural': 'statuses',
            },
        ),
        migrations.CreateModel(
            name='TestList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, db_index=True)),
                ('slug', models.SlugField(help_text='A short unique name for use in the URL of this list', unique=True)),
                ('description', models.TextField(help_text='A concise description of this test checklist. (You may use HTML markup)', null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('warning_message', models.CharField(default=b'Do not treat', help_text='Message given when a test value is out of tolerance', max_length=255)),
                ('created_by', models.ForeignKey(related_name='qa_testlist_created', editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(related_name='qa_testlist_modified', editable=False, to=settings.AUTH_USER_MODEL)),
                ('sublists', models.ManyToManyField(help_text='Choose any sublists that should be performed as part of this list.', to='qa.TestList', blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TestListCycle',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, db_index=True)),
                ('slug', models.SlugField(help_text='A short unique name for use in the URL of this list', unique=True)),
                ('description', models.TextField(help_text='A concise description of this test checklist. (You may use HTML markup)', null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('drop_down_label', models.CharField(default=b'Choose Day', max_length=128)),
                ('day_option_text', models.CharField(default=b'day', max_length=8, choices=[(b'day', b'Day'), (b'tlname', b'Test List Name')])),
                ('created_by', models.ForeignKey(related_name='qa_testlistcycle_created', editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(related_name='qa_testlistcycle_modified', editable=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TestListCycleMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.IntegerField()),
                ('cycle', models.ForeignKey(to='qa.TestListCycle')),
                ('test_list', models.ForeignKey(to='qa.TestList')),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='TestListInstance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('work_started', models.DateTimeField(db_index=True)),
                ('work_completed', models.DateTimeField(default=django.utils.timezone.now, null=True, db_index=True)),
                ('comment', models.TextField(help_text='Add a comment to this set of tests', null=True, blank=True)),
                ('in_progress', models.BooleanField(default=False, help_text='Mark this session as still in progress so you can complete later (will not be submitted for review)', db_index=True)),
                ('reviewed', models.DateTimeField(null=True, blank=True)),
                ('all_reviewed', models.BooleanField(default=False)),
                ('day', models.IntegerField(default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField()),
                ('created_by', models.ForeignKey(related_name='test_list_instance_creator', editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(related_name='test_list_instance_modifier', editable=False, to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(related_name='test_list_instance_reviewer', blank=True, editable=False, to=settings.AUTH_USER_MODEL, null=True)),
                ('test_list', models.ForeignKey(editable=False, to='qa.TestList')),
            ],
            options={
                'get_latest_by': 'work_completed',
                'permissions': (('can_override_date', 'Can override date'), ('can_perform_subset', 'Can perform subset of tests'), ('can_view_completed', 'Can view previously completed instances')),
            },
        ),
        migrations.CreateModel(
            name='TestListMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.IntegerField(db_index=True)),
                ('test', models.ForeignKey(to='qa.Test')),
                ('test_list', models.ForeignKey(to='qa.TestList')),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='Tolerance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(help_text='Select whether this will be an absolute or relative tolerance criteria', max_length=20, choices=[(b'absolute', b'Absolute'), (b'percent', b'Percentage'), (b'multchoice', b'Multiple Choice')])),
                ('act_low', models.FloatField(help_text='Value of lower Action level', null=True, verbose_name='Action Low', blank=True)),
                ('tol_low', models.FloatField(help_text='Value of lower Tolerance level', null=True, verbose_name='Tolerance Low', blank=True)),
                ('tol_high', models.FloatField(help_text='Value of upper Tolerance level', null=True, verbose_name='Tolerance High', blank=True)),
                ('act_high', models.FloatField(help_text='Value of upper Action level', null=True, verbose_name='Action High', blank=True)),
                ('mc_pass_choices', models.CharField(help_text='Comma seperated list of choices that are considered passing', max_length=2048, null=True, verbose_name='Multiple Choice OK Values', blank=True)),
                ('mc_tol_choices', models.CharField(help_text='Comma seperated list of choices that are considered at tolerance', max_length=2048, null=True, verbose_name='Multiple Choice Tolerance Values', blank=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(related_name='tolerance_creators', editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(related_name='tolerance_modifiers', editable=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['type', 'act_low', 'tol_low', 'tol_high', 'act_high'],
            },
        ),
        migrations.CreateModel(
            name='UnitTestCollection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('due_date', models.DateTimeField(help_text='Next time this item is due', null=True, blank=True)),
                ('auto_schedule', models.BooleanField(default=True, help_text='If this is checked, due_date will be auto set based on the assigned frequency')),
                ('active', models.BooleanField(default=True, help_text='Uncheck to disable this test on this unit', db_index=True)),
                ('object_id', models.PositiveIntegerField()),
                ('assigned_to', models.ForeignKey(to='auth.Group', help_text='QA group that this test list should nominally be performed by', null=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('frequency', models.ForeignKey(blank=True, to='qa.Frequency', help_text='Frequency with which this test list is to be performed', null=True)),
                ('last_instance', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, editable=False, to='qa.TestListInstance', null=True)),
                ('unit', models.ForeignKey(to='units.Unit')),
                ('visible_to', models.ManyToManyField(help_text='Select groups who will be able to see this test collection on this unit', related_name='test_collection_visibility', to='auth.Group')),
            ],
            options={
                'verbose_name_plural': 'Assign Test Lists to Units',
                'permissions': (('can_view_overview', 'Can view program overview'), ('can_review_non_visible_tli', "Can view tli and utc not visible to user's groups")),
            },
        ),
        migrations.CreateModel(
            name='UnitTestInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('active', models.BooleanField(default=True, help_text='Uncheck to disable this test on this unit', db_index=True)),
                ('assigned_to', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='auth.Group', help_text='QA group that this test list should nominally be performed by', null=True)),
                ('reference', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='Current Reference', blank=True, to='qa.Reference', null=True)),
                ('test', models.ForeignKey(to='qa.Test')),
                ('tolerance', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='qa.Tolerance', null=True)),
                ('unit', models.ForeignKey(to='units.Unit')),
            ],
            options={
                'verbose_name_plural': 'Set References & Tolerances',
                'permissions': (('can_view_ref_tol', 'Can view Refs and Tols'),),
            },
        ),
        migrations.AddField(
            model_name='testlistinstance',
            name='unit_test_collection',
            field=models.ForeignKey(editable=False, to='qa.UnitTestCollection'),
        ),
        migrations.AddField(
            model_name='testlistcycle',
            name='test_lists',
            field=models.ManyToManyField(to='qa.TestList', through='qa.TestListCycleMembership'),
        ),
        migrations.AddField(
            model_name='testlist',
            name='tests',
            field=models.ManyToManyField(help_text='Which tests does this list contain', to='qa.Test', through='qa.TestListMembership'),
        ),
        migrations.AddField(
            model_name='testinstance',
            name='status',
            field=models.ForeignKey(to='qa.TestInstanceStatus'),
        ),
        migrations.AddField(
            model_name='testinstance',
            name='test_list_instance',
            field=models.ForeignKey(editable=False, to='qa.TestListInstance'),
        ),
        migrations.AddField(
            model_name='testinstance',
            name='tolerance',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, editable=False, to='qa.Tolerance', null=True),
        ),
        migrations.AddField(
            model_name='testinstance',
            name='unit_test_info',
            field=models.ForeignKey(editable=False, to='qa.UnitTestInfo'),
        ),
        migrations.AddField(
            model_name='autoreviewrule',
            name='status',
            field=models.ForeignKey(to='qa.TestInstanceStatus'),
        ),
        migrations.AlterUniqueTogether(
            name='unittestinfo',
            unique_together=set([('test', 'unit')]),
        ),
        migrations.AlterUniqueTogether(
            name='unittestcollection',
            unique_together=set([('unit', 'frequency', 'content_type', 'object_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='testlistmembership',
            unique_together=set([('test_list', 'test')]),
        ),
    ]
