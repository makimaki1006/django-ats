"""
Django ATS - Dashboard URLs
"""

from django.urls import path

from .views import DashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]
