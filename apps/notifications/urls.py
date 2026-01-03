"""Django ATS - Notifications URLs"""
from django.urls import path

from .views import (
    NotificationListView,
    NotificationDropdownView,
    NotificationUnreadCountView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
    NotificationDeleteView,
    NotificationClearAllView,
)

app_name = 'notifications'

urlpatterns = [
    # 一覧
    path('', NotificationListView.as_view(), name='notification_list'),

    # HTMX用エンドポイント
    path('dropdown/', NotificationDropdownView.as_view(), name='dropdown'),
    path('unread-count/', NotificationUnreadCountView.as_view(), name='unread_count'),

    # 既読操作
    path('<uuid:pk>/mark-read/', NotificationMarkReadView.as_view(), name='mark_read'),
    path('mark-all-read/', NotificationMarkAllReadView.as_view(), name='mark_all_read'),

    # 削除
    path('<uuid:pk>/delete/', NotificationDeleteView.as_view(), name='delete'),
    path('clear-all/', NotificationClearAllView.as_view(), name='clear_all'),
]
