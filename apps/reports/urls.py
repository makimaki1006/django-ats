"""Django ATS - Reports URLs"""
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class ReportsIndexView(LoginRequiredMixin, TemplateView):
    """レポートインデックス（スタブ）"""
    template_name = 'reports/index.html'


app_name = 'reports'

urlpatterns = [
    path('', ReportsIndexView.as_view(), name='index'),
]
