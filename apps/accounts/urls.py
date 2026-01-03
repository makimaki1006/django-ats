"""
Django ATS - Accounts URLs
"""

from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # プロファイル
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),

    # パスワード変更
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    # ログアウト
    path('logout/confirm/', views.LogoutConfirmView.as_view(), name='logout_confirm'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # ユーザー管理（管理者用）
    path('', views.UserListView.as_view(), name='user_list'),
    path('create/', views.UserCreateView.as_view(), name='user_create'),
    path('<uuid:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('<uuid:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('<uuid:pk>/toggle-active/', views.UserToggleActiveView.as_view(), name='user_toggle_active'),

    # テナント切り替え（システム管理者用）
    path('tenant-switch/', views.TenantSwitchView.as_view(), name='tenant_switch'),

    # 監査ログ
    path('audit-logs/', views.AuditLogListView.as_view(), name='audit_log_list'),
    path('audit-logs/<uuid:pk>/', views.AuditLogDetailView.as_view(), name='audit_log_detail'),

    # ログイン履歴
    path('login-history/', views.LoginHistoryListView.as_view(), name='login_history_list'),
    path('my-login-history/', views.MyLoginHistoryView.as_view(), name='my_login_history'),
]
