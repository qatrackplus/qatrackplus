from django.conf import settings

if settings.USE_SERVICE_LOG:
    from qatrack.reports.service_log.details import ServiceEventDetailsReport
    from qatrack.reports.service_log.summary import ServiceEventSummaryReport
    from qatrack.reports.service_log.personnel import ServiceEventPersonnelSummaryReport
    from qatrack.reports.service_log.service_times import ServiceTimesReport
