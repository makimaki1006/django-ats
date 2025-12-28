"""
Django ATS - 応募URL
"""

from django.urls import path

from . import views

app_name = 'applications'

urlpatterns = [
    # 応募一覧・管理
    path('', views.ApplicationListView.as_view(), name='application_list'),
    path('create/', views.ApplicationCreateView.as_view(), name='application_create'),
    path('kanban/', views.ApplicationKanbanView.as_view(), name='application_kanban'),
    path('<uuid:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('<uuid:pk>/edit/', views.ApplicationUpdateView.as_view(), name='application_update'),
    path('<uuid:pk>/status/', views.ApplicationStatusChangeView.as_view(), name='application_status'),

    # 統合応募フォーム
    path('apply/', views.UnifiedApplicationFormView.as_view(), name='unified_form'),
    path('apply/complete/<uuid:pk>/', views.UnifiedApplicationCompleteView.as_view(), name='unified_complete'),
]
