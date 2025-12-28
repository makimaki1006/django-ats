"""
Django ATS - 候補者URL
"""

from django.urls import path

from . import views

app_name = 'candidates'

urlpatterns = [
    # 候補者CRUD
    path('', views.CandidateListView.as_view(), name='candidate_list'),
    path('create/', views.CandidateCreateView.as_view(), name='candidate_create'),
    path('<uuid:pk>/', views.CandidateDetailView.as_view(), name='candidate_detail'),
    path('<uuid:pk>/edit/', views.CandidateUpdateView.as_view(), name='candidate_update'),
    path('<uuid:pk>/archive/', views.CandidateArchiveView.as_view(), name='candidate_archive'),
    path('search/', views.CandidateQuickSearchView.as_view(), name='candidate_search'),

    # CSVインポート
    path('import/', views.CSVImportView.as_view(), name='csv_import'),
    path('import/result/<uuid:pk>/', views.CSVImportResultView.as_view(), name='csv_import_result'),
    path('import/template/', views.CSVTemplateDownloadView.as_view(), name='csv_template_download'),
    path('import/history/', views.CSVImportHistoryView.as_view(), name='csv_import_history'),

    # コメント
    path('<uuid:candidate_pk>/comments/', views.CandidateCommentCreateView.as_view(), name='comment_create'),
    path('<uuid:candidate_pk>/comments/<uuid:comment_pk>/edit/', views.CandidateCommentUpdateView.as_view(), name='comment_update'),
    path('<uuid:candidate_pk>/comments/<uuid:comment_pk>/delete/', views.CandidateCommentDeleteView.as_view(), name='comment_delete'),
]
