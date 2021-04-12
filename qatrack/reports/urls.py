from django.urls import path

import qatrack.reports.views as views

urlpatterns = [
    path('', views.select_report, name="reports"),
    path('filter/', views.get_filter, name="reports-filter"),
    path('preview/', views.report_preview, name="reports-preview"),
    path('save/', views.save_report, name="reports-save"),
    path('load/', views.load_report, name="reports-load"),
    path('delete/', views.delete_report, name="reports-delete"),
    path('saved-reports/', views.saved_reports_datatable, name="reports-saved"),
    path('schedule/<int:report_id>/', views.report_schedule_form, name="reports-schedule-form"),
    path('schedule/delete/', views.delete_schedule, name="reports-schedule-delete"),
    path('schedule/', views.schedule_report, name="reports-schedule"),
]
