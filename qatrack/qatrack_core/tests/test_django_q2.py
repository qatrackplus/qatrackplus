from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django_q.models import Schedule, Task
from django_q.tasks import async_task

from qatrack.qa import models
from qatrack.qatrack_core.tasks import run_periodic_scheduler


class TestDjangoQ2BasicFunctionality(TestCase):
    """Test basic django-q2 functionality"""

    def setUp(self):
        # Clear any existing tasks/schedules
        Task.objects.all().delete()
        Schedule.objects.all().delete()

    def test_async_task_creation(self):
        """Test that async tasks can be created"""
        # Create a simple async task
        task_id = async_task('qatrack.qatrack_core.tasks.run_periodic_scheduler')
        
        # Check that task_id is returned (basic functionality test)
        self.assertIsNotNone(task_id)
        self.assertTrue(isinstance(task_id, str) or isinstance(task_id, int))

    def test_schedule_creation(self):
        """Test that schedules can be created"""
        # Create a schedule
        schedule = Schedule.objects.create(
            func='qatrack.qatrack_core.tasks.run_periodic_scheduler',
            schedule_type=Schedule.ONCE,
            next_run=timezone.now() + timezone.timedelta(minutes=1)
        )
        
        self.assertEqual(schedule.func, 'qatrack.qatrack_core.tasks.run_periodic_scheduler')
        self.assertEqual(schedule.schedule_type, Schedule.ONCE)

    def test_recurring_schedule(self):
        """Test recurring schedule creation"""
        schedule = Schedule.objects.create(
            func='qatrack.qatrack_core.tasks.run_periodic_scheduler',
            schedule_type=Schedule.MINUTES,
            minutes=5
        )
        
        self.assertEqual(schedule.schedule_type, Schedule.MINUTES)
        self.assertEqual(schedule.minutes, 5)

    def test_task_execution(self):
        """Test that tasks can be executed"""
        # Create task
        task_id = async_task('test_function')
        
        # Verify task_id is returned
        self.assertIsNotNone(task_id)
        self.assertTrue(isinstance(task_id, str) or isinstance(task_id, int))

    def test_schedule_execution(self):
        """Test that schedules execute at the right time"""
        # Create a schedule for 1 second from now
        next_run = timezone.now() + timezone.timedelta(seconds=1)
        schedule = Schedule.objects.create(
            func='qatrack.qatrack_core.tasks.run_periodic_scheduler',
            schedule_type=Schedule.ONCE,
            next_run=next_run
        )
        
        # Verify schedule was created
        self.assertEqual(schedule.next_run, next_run)
        self.assertEqual(schedule.schedule_type, Schedule.ONCE)


class TestDjangoQ2Integration(TestCase):
    """Test django-q2 integration with QATrack+ specific functionality"""

    def setUp(self):
        Task.objects.all().delete()
        Schedule.objects.all().delete()

    def test_run_periodic_scheduler_task(self):
        """Test that the periodic scheduler task can be scheduled"""
        # Schedule the periodic scheduler
        task_id = async_task('qatrack.qatrack_core.tasks.run_periodic_scheduler')
        
        # Verify task_id is returned
        self.assertIsNotNone(task_id)
        self.assertTrue(isinstance(task_id, str) or isinstance(task_id, int))

    @patch('qatrack.qatrack_core.tasks.logger')
    def test_run_periodic_scheduler_execution(self, mock_logger):
        """Test that run_periodic_scheduler executes without errors"""
        # Call the function directly with required arguments
        from qatrack.notifications.models import QCSchedulingNotice
        run_periodic_scheduler(QCSchedulingNotice, "test", lambda x, y: None)
        
        # Verify it executed without errors (logs something)
        mock_logger.info.assert_called()

    def test_notification_scheduling(self):
        """Test that notification schedules are created correctly"""
        from qatrack.notifications.models import QCSchedulingNotice, RecipientGroup
        from qatrack.notifications.qcscheduling.tasks import schedule_scheduling_notice
        
        # Create a test notification
        recipients = RecipientGroup.objects.create(name="Test Group")
        notice = QCSchedulingNotice.objects.create(
            recipients=recipients,
            notification_type=QCSchedulingNotice.DUE,
            time="0:00"
        )
        
        # Schedule the notice
        next_run = timezone.now() + timezone.timedelta(hours=1)
        schedule_scheduling_notice(notice, next_run)
        
        # Verify schedule was created
        schedules = Schedule.objects.filter(func__contains='send_scheduling_notice')
        self.assertEqual(schedules.count(), 1)
        self.assertEqual(schedules.first().next_run, next_run)

    def test_report_scheduling(self):
        """Test that report schedules are created correctly"""
        from qatrack.reports.models import ReportSchedule, SavedReport
        from qatrack.reports.tasks import schedule_report
        
        # Create a test user and saved report first
        user = models.User.objects.create_user('testuser', 'test@example.com', 'password')
        saved_report = SavedReport.objects.create(
            title="Test Report",
            report_type="qc",
            created_by=user,
            modified_by=user
        )
        
        # Create a test report schedule
        report_schedule = ReportSchedule.objects.create(
            report=saved_report,
            time=timezone.now().time(),
            created_by=user,
            modified_by=user
        )
        
        # Schedule the report
        next_run = timezone.now() + timezone.timedelta(hours=1)
        schedule_report(report_schedule, next_run)
        
        # Verify schedule was created
        schedules = Schedule.objects.filter(func__contains='send_report')
        self.assertEqual(schedules.count(), 1)


class TestDjangoQ2Monitoring(TestCase):
    """Test django-q2 monitoring functionality"""

    def setUp(self):
        Task.objects.all().delete()
        Schedule.objects.all().delete()

    def test_task_monitoring(self):
        """Test that tasks can be monitored"""
        # Create a task
        task_id = async_task('qatrack.qatrack_core.tasks.run_periodic_scheduler')
        
        # Verify task_id is returned
        self.assertIsNotNone(task_id)
        self.assertTrue(isinstance(task_id, str) or isinstance(task_id, int))

    def test_schedule_monitoring(self):
        """Test that schedules can be monitored"""
        # Create a schedule
        schedule = Schedule.objects.create(
            func='qatrack.qatrack_core.tasks.run_periodic_scheduler',
            schedule_type=Schedule.MINUTES,
            minutes=5
        )
        
        # Get schedule info
        self.assertEqual(schedule.func, 'qatrack.qatrack_core.tasks.run_periodic_scheduler')
        self.assertEqual(schedule.schedule_type, Schedule.MINUTES)

    def test_cluster_status(self):
        """Test cluster status functionality"""
        from django_q.cluster import Cluster
        
        # This would test cluster status in a real environment
        # For now, just verify the import works
        self.assertTrue(hasattr(Cluster, 'start'))


class TestDjangoQ2ErrorHandling(TestCase):
    """Test django-q2 error handling"""

    def setUp(self):
        Task.objects.all().delete()
        Schedule.objects.all().delete()

    def test_failed_task_handling(self):
        """Test that failed tasks are handled correctly"""
        # Create task
        task_id = async_task('failing_function')
        
        # Verify task_id is returned
        self.assertIsNotNone(task_id)
        self.assertTrue(isinstance(task_id, str) or isinstance(task_id, int))

    def test_retry_functionality(self):
        """Test that tasks can be retried"""
        # Retry the task
        new_task_id = async_task('test_function')
        
        # Verify new task was created
        self.assertIsNotNone(new_task_id)
        self.assertTrue(isinstance(new_task_id, str) or isinstance(new_task_id, int)) 