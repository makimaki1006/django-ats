"""Django ATS - Agents URLs"""
from django.urls import path

from .views import (
    AgentCompanyListView,
    AgentCompanyDetailView,
    AgentCompanyCreateView,
    AgentCompanyUpdateView,
    AgentCompanyDeleteView,
    AgentCompanyToggleActiveView,
    AgentCompanyTogglePreferredView,
    AgentCompanyUpdateStatsView,
)

app_name = 'agents'

urlpatterns = [
    path('', AgentCompanyListView.as_view(), name='agent_list'),
    path('create/', AgentCompanyCreateView.as_view(), name='agent_create'),
    path('<uuid:pk>/', AgentCompanyDetailView.as_view(), name='agent_detail'),
    path('<uuid:pk>/edit/', AgentCompanyUpdateView.as_view(), name='agent_update'),
    path('<uuid:pk>/delete/', AgentCompanyDeleteView.as_view(), name='agent_delete'),
    path('<uuid:pk>/toggle-active/', AgentCompanyToggleActiveView.as_view(), name='agent_toggle_active'),
    path('<uuid:pk>/toggle-preferred/', AgentCompanyTogglePreferredView.as_view(), name='agent_toggle_preferred'),
    path('<uuid:pk>/update-stats/', AgentCompanyUpdateStatsView.as_view(), name='agent_update_stats'),
]
