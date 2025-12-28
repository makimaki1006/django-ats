"""Django ATS - Agents URLs"""
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class AgentListView(LoginRequiredMixin, TemplateView):
    """エージェント一覧（スタブ）"""
    template_name = 'agents/agent_list.html'


app_name = 'agents'

urlpatterns = [
    path('', AgentListView.as_view(), name='agent_list'),
]
