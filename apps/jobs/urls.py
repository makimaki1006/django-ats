"""
Django ATS - 求人URL
"""

from django.urls import path

from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.JobListView.as_view(), name='job_list'),
    path('create/', views.JobCreateView.as_view(), name='job_create'),
    path('<uuid:pk>/', views.JobDetailView.as_view(), name='job_detail'),
    path('<uuid:pk>/edit/', views.JobUpdateView.as_view(), name='job_update'),
    path('<uuid:pk>/status/<str:action>/', views.JobStatusChangeView.as_view(), name='job_status'),
    path('<uuid:pk>/duplicate/', views.JobDuplicateView.as_view(), name='job_duplicate'),
]
