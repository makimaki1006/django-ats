"""Django ATS - Settings URLs"""
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class SettingsIndexView(LoginRequiredMixin, TemplateView):
    """設定インデックス（スタブ）"""
    template_name = 'settings/index.html'


app_name = 'settings'

urlpatterns = [
    path('', SettingsIndexView.as_view(), name='index'),
]
