"""Django ATS - Personas URLs"""
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class PersonaListView(LoginRequiredMixin, TemplateView):
    """ペルソナ一覧（スタブ）"""
    template_name = 'personas/persona_list.html'


app_name = 'personas'

urlpatterns = [
    path('', PersonaListView.as_view(), name='persona_list'),
]
