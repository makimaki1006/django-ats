"""Django ATS - Tenants URLs"""
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class TenantListView(LoginRequiredMixin, TemplateView):
    """テナント一覧（スタブ）"""
    template_name = 'tenants/tenant_list.html'


app_name = 'tenants'

urlpatterns = [
    path('', TenantListView.as_view(), name='tenant_list'),
]
