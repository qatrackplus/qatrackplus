from django.conf import settings

if settings.USE_SERVICE_LOG:
    from qatrack.reports.service_log.details import ServiceEventDetailsReport
    from qatrack.reports.service_log.summary import ServiceEventSummaryReport
