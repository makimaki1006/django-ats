"""Django ATS - Settings URLs"""
from django.urls import path

from .views import (
    # インデックス
    SettingsIndexView,
    # StatusSetting
    StatusSettingListView,
    StatusSettingCreateView,
    StatusSettingUpdateView,
    StatusSettingDeleteView,
    StatusSettingReorderView,
    # ApplicationSource
    ApplicationSourceListView,
    ApplicationSourceCreateView,
    ApplicationSourceUpdateView,
    ApplicationSourceDeleteView,
    # EmailTemplate
    EmailTemplateListView,
    EmailTemplateCreateView,
    EmailTemplateUpdateView,
    EmailTemplateDeleteView,
    EmailTemplatePreviewView,
    EmailTemplateDuplicateView,
    # SpreadsheetConnection
    SpreadsheetConnectionDetailView,
    SpreadsheetConnectionCreateView,
    SpreadsheetConnectionUpdateView,
    SpreadsheetConnectionDeleteView,
    SpreadsheetTestConnectionView,
    SpreadsheetSyncView,
)

app_name = 'settings'

urlpatterns = [
    # インデックス
    path('', SettingsIndexView.as_view(), name='index'),

    # StatusSetting CRUD
    path('status/', StatusSettingListView.as_view(), name='status_list'),
    path('status/create/', StatusSettingCreateView.as_view(), name='status_create'),
    path('status/<uuid:pk>/edit/', StatusSettingUpdateView.as_view(), name='status_update'),
    path('status/<uuid:pk>/delete/', StatusSettingDeleteView.as_view(), name='status_delete'),
    path('status/reorder/', StatusSettingReorderView.as_view(), name='status_reorder'),

    # ApplicationSource CRUD
    path('sources/', ApplicationSourceListView.as_view(), name='source_list'),
    path('sources/create/', ApplicationSourceCreateView.as_view(), name='source_create'),
    path('sources/<uuid:pk>/edit/', ApplicationSourceUpdateView.as_view(), name='source_update'),
    path('sources/<uuid:pk>/delete/', ApplicationSourceDeleteView.as_view(), name='source_delete'),

    # EmailTemplate CRUD
    path('templates/', EmailTemplateListView.as_view(), name='template_list'),
    path('templates/create/', EmailTemplateCreateView.as_view(), name='template_create'),
    path('templates/<uuid:pk>/edit/', EmailTemplateUpdateView.as_view(), name='template_update'),
    path('templates/<uuid:pk>/delete/', EmailTemplateDeleteView.as_view(), name='template_delete'),
    path('templates/<uuid:pk>/preview/', EmailTemplatePreviewView.as_view(), name='template_preview'),
    path('templates/<uuid:pk>/duplicate/', EmailTemplateDuplicateView.as_view(), name='template_duplicate'),

    # SpreadsheetConnection
    path('spreadsheet/', SpreadsheetConnectionDetailView.as_view(), name='spreadsheet_detail'),
    path('spreadsheet/create/', SpreadsheetConnectionCreateView.as_view(), name='spreadsheet_create'),
    path('spreadsheet/edit/', SpreadsheetConnectionUpdateView.as_view(), name='spreadsheet_update'),
    path('spreadsheet/delete/', SpreadsheetConnectionDeleteView.as_view(), name='spreadsheet_delete'),
    path('spreadsheet/test/', SpreadsheetTestConnectionView.as_view(), name='spreadsheet_test'),
    path('spreadsheet/sync/', SpreadsheetSyncView.as_view(), name='spreadsheet_sync'),
]
