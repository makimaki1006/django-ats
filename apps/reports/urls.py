"""Django ATS - Reports URLs"""
from django.urls import path

from .views import (
    ReportsDashboardView,
    ApplicationsReportView,
    InterviewsReportView,
    ExportCSVView,
)


app_name = 'reports'

urlpatterns = [
    # ダッシュボード
    path('', ReportsDashboardView.as_view(), name='index'),
    path('dashboard/', ReportsDashboardView.as_view(), name='dashboard'),

    # 個別レポート
    path('applications/', ApplicationsReportView.as_view(), name='applications'),
    path('interviews/', InterviewsReportView.as_view(), name='interviews'),

    # CSVエクスポート
    path('export/<str:report_type>/', ExportCSVView.as_view(), name='export_csv'),
]
