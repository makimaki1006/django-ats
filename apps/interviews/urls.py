"""
Django ATS - 面接URL
"""

from django.urls import path

from . import views

app_name = 'interviews'

urlpatterns = [
    # 面接一覧・CRUD
    path('', views.InterviewListView.as_view(), name='interview_list'),
    path('create/', views.InterviewCreateView.as_view(), name='interview_create'),
    path('calendar/', views.InterviewCalendarView.as_view(), name='interview_calendar'),
    path('<uuid:pk>/', views.InterviewDetailView.as_view(), name='interview_detail'),
    path('<uuid:pk>/edit/', views.InterviewUpdateView.as_view(), name='interview_update'),
    path('<uuid:pk>/result/', views.InterviewResultView.as_view(), name='interview_result'),
    path('<uuid:pk>/cancel/', views.InterviewCancelView.as_view(), name='interview_cancel'),

    # 面接サポート（面接官向け）
    path('support/', views.InterviewSupportDashboardView.as_view(), name='interview_support_dashboard'),
    path('support/<uuid:pk>/', views.InterviewSupportDetailView.as_view(), name='interview_support_detail'),
    path('support/<uuid:pk>/evaluate/', views.InterviewQuickEvaluationView.as_view(), name='interview_quick_evaluation'),
]
