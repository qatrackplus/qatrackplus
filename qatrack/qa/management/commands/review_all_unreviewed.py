from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from qatrack.qa.models import (
    TestInstance,
    ReviewStatus,
    TestListInstance,
    User,
)
from qatrack.service_log.models import ServiceEvent, ServiceLog


class Command(BaseCommand):
    """A management command to review all unreviewed TestListInstances"""

    help = 'Command to mark all unreviewed TestListInstances as reviewed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            nargs=1,
            required=True,
            dest="user",
            help="The username to use as the reviewer",
            type=str,
        )
        parser.add_argument(
            '--status',
            required=True,
            nargs=1,
            dest="status",
            help="The testinstance status slug to use as the review status",
            type=str,
        )

    def handle(self, *args, **kwargs):

        all_status = ReviewStatus.objects.all()
        status = all_status.filter(slug=kwargs['status'][0]).first()
        if not status:
            print(
                "'%s' is not a valid status slug. Options are: %s" % (
                    kwargs['status'][0],
                    ', '.join(all_status.values_list("slug", flat=True))
                )
            )
            return

        users = User.objects.all()
        user = users.filter(username=kwargs['user'][0]).first()
        if not user:
            print("'%s' is not a valid username." % kwargs['user'][0])
            return

        objs = TestListInstance.objects.unreviewed()
        counts = objs.count()

        if counts <= 0:
            print("No unreviewed instances")
            return

        prompt = (
            "Are you sure you want to set the review status of %d unreviewed TestListInstances to %s (y/N): " % (
                counts, status
            )
        )

        confirm = input(prompt)
        if confirm.lower() != 'y':
            print("Action cancelled")
            return

        review_time = timezone.now()

        for tli in objs:
            tli.reviewed = review_time
            tli.reviewed_by = user
            tli.all_reviewed = True
            tli.save()

            TestInstance.objects.filter(test_list_instance=tli).update(
                status=status,
                review_date=review_time,
                reviewed_by=user,
            )

            # Handle Service Log items:
            #    Log changes to this test_list_instance review status if linked to service_events via rtsqa.
            for se in ServiceEvent.objects.filter(returntoserviceqa__test_list_instance=tli):
                ServiceLog.objects.log_rtsqa_changes(user, se)

            # Set utc due dates
            tli.unit_test_collection.set_due_date()

        cache.delete(settings.CACHE_UNREVIEWED_COUNT)
        cache.delete(settings.CACHE_UNREVIEWED_COUNT_USER)
        cache.delete(settings.CACHE_SE_NEEDING_REVIEW_COUNT)

        print("%s TestListInstances updated with status=%s by user=%s" % (counts, status, user.username))
