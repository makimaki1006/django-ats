"""Django ATS - Notifications URLs"""
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class NotificationListView(LoginRequiredMixin, TemplateView):
    """通知一覧（スタブ）"""
    template_name = 'notifications/notification_list.html'


class NotificationListPartialView(LoginRequiredMixin, TemplateView):
    """通知一覧パーシャル（スタブ）"""
    template_name = 'notifications/notification_list_partial.html'


app_name = 'notifications'

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification_list'),
    path('partial/', NotificationListPartialView.as_view(), name='notification_list_partial'),
]
