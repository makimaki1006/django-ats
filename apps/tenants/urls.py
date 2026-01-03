"""Django ATS - Tenants URLs

テナント管理用URLパターン。
すべて管理者専用。
"""

from django.urls import path

from apps.tenants.views import (
    TenantListView,
    TenantDetailView,
    TenantCreateView,
    TenantUpdateView,
    TenantToggleActiveView,
    TenantStatsView,
    TenantSpreadsheetUpdateView,
    TenantSpreadsheetDeleteView,
    TenantSpreadsheetSyncView,
    TenantSpreadsheetStatusView,
)


app_name = 'tenants'

urlpatterns = [
    # テナントCRUD
    path('', TenantListView.as_view(), name='tenant_list'),
    path('create/', TenantCreateView.as_view(), name='tenant_create'),
    path('<uuid:pk>/', TenantDetailView.as_view(), name='tenant_detail'),
    path('<uuid:pk>/edit/', TenantUpdateView.as_view(), name='tenant_update'),
    path('<uuid:pk>/toggle-active/', TenantToggleActiveView.as_view(), name='tenant_toggle_active'),
    path('<uuid:pk>/stats/', TenantStatsView.as_view(), name='tenant_stats'),

    # スプレッドシート接続
    path('<uuid:pk>/spreadsheet/', TenantSpreadsheetUpdateView.as_view(), name='tenant_spreadsheet'),
    path('<uuid:pk>/spreadsheet/delete/', TenantSpreadsheetDeleteView.as_view(), name='tenant_spreadsheet_delete'),
    path('<uuid:pk>/spreadsheet/sync/', TenantSpreadsheetSyncView.as_view(), name='tenant_spreadsheet_sync'),
    path('<uuid:pk>/spreadsheet/status/', TenantSpreadsheetStatusView.as_view(), name='tenant_spreadsheet_status'),
]
