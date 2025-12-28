"""
Django ATS - Core URLs
"""

from django.urls import path
from django.views.generic import RedirectView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class GlobalSearchView(LoginRequiredMixin, TemplateView):
    """グローバル検索（スタブ）"""
    template_name = 'core/search.html'


app_name = 'core'

urlpatterns = [
    # ルートURLはダッシュボードにリダイレクト
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='index'),
    # グローバル検索
    path('search/', GlobalSearchView.as_view(), name='search'),
]
