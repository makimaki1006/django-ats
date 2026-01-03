"""
Django ATS - エージェントビュー
エージェント会社の一覧、詳細、作成、更新、削除
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    View,
)

from apps.core.mixins import (
    HtmxMixin,
    PaginationMixin,
    SearchMixin,
)
from .models import AgentCompany
from .forms import AgentCompanyForm, AgentCompanyFilterForm


class AgentCompanyQuerysetMixin:
    """エージェント会社のクエリセット制御

    テナント固有 + グローバル（tenant=null）のエージェントを返す
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            # テナント固有 OR グローバル（tenant=null）
            queryset = queryset.filter(
                Q(tenant=tenant) | Q(tenant__isnull=True)
            )
        return queryset


class AgentCompanyListView(
    LoginRequiredMixin,
    AgentCompanyQuerysetMixin,
    SearchMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """エージェント会社一覧"""
    model = AgentCompany
    template_name = 'agents/agent_list.html'
    context_object_name = 'agents'
    search_fields = ['name', 'code', 'contact_person', 'contact_email']
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()

        # 有効フィルタ
        is_active = self.request.GET.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        # 優先パートナーフィルタ
        is_preferred = self.request.GET.get('is_preferred')
        if is_preferred == 'true':
            queryset = queryset.filter(is_preferred=True)

        # グローバル/テナント固有フィルタ
        scope = self.request.GET.get('scope')
        if scope == 'global':
            queryset = queryset.filter(tenant__isnull=True)
        elif scope == 'tenant':
            queryset = queryset.filter(tenant__isnull=False)

        return queryset.annotate(
            candidate_count=Count('candidates')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = AgentCompanyFilterForm(self.request.GET)
        return context


class AgentCompanyDetailView(
    LoginRequiredMixin,
    AgentCompanyQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """エージェント会社詳細"""
    model = AgentCompany
    template_name = 'agents/agent_detail.html'
    context_object_name = 'agent'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.prefetch_related('candidates')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 最近の候補者を取得
        context['recent_candidates'] = self.object.candidates.order_by(
            '-created_at'
        )[:10]
        # 関連する求人を取得
        context['linked_jobs'] = [
            ja.job for ja in self.object.agent_jobs.select_related('job').all()
        ]
        return context


class AgentCompanyCreateView(
    LoginRequiredMixin,
    HtmxMixin,
    CreateView
):
    """エージェント会社作成"""
    model = AgentCompany
    form_class = AgentCompanyForm
    template_name = 'agents/agent_form.html'
    success_url = reverse_lazy('agents:agent_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        agent = form.save(commit=False)
        # テナント固有として作成（グローバルは管理者のみ）
        agent.tenant = self.request.tenant
        agent.save()
        messages.success(self.request, f'エージェント「{agent.name}」を登録しました。')
        return super().form_valid(form)


class AgentCompanyUpdateView(
    LoginRequiredMixin,
    AgentCompanyQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """エージェント会社更新"""
    model = AgentCompany
    form_class = AgentCompanyForm
    template_name = 'agents/agent_form.html'

    def get_queryset(self):
        # グローバルエージェントは編集不可（テナント固有のみ）
        queryset = super().get_queryset()
        return queryset.filter(tenant=self.request.tenant)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_success_url(self):
        return reverse_lazy('agents:agent_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'エージェント「{form.instance.name}」を更新しました。')
        return super().form_valid(form)


class AgentCompanyDeleteView(
    LoginRequiredMixin,
    AgentCompanyQuerysetMixin,
    HtmxMixin,
    View
):
    """エージェント会社削除"""

    def post(self, request, pk, *args, **kwargs):
        # テナント固有のエージェントのみ削除可能
        queryset = AgentCompany.objects.filter(tenant=request.tenant)
        agent = get_object_or_404(queryset, pk=pk)

        # 関連する候補者があれば削除不可
        if agent.candidates.exists():
            messages.error(
                request,
                f'エージェント「{agent.name}」は候補者に紐付いているため削除できません。'
            )
            if request.htmx:
                return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
            return redirect('agents:agent_list')

        name = agent.name
        agent.delete()
        messages.success(request, f'エージェント「{name}」を削除しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('agents:agent_list')


class AgentCompanyToggleActiveView(
    LoginRequiredMixin,
    AgentCompanyQuerysetMixin,
    HtmxMixin,
    View
):
    """エージェント会社有効/無効切り替え"""

    def post(self, request, pk, *args, **kwargs):
        # テナント固有のエージェントのみ切り替え可能
        queryset = AgentCompany.objects.filter(tenant=request.tenant)
        agent = get_object_or_404(queryset, pk=pk)

        agent.is_active = not agent.is_active
        agent.save(update_fields=['is_active', 'updated_at'])

        status = '有効' if agent.is_active else '無効'
        messages.success(request, f'エージェント「{agent.name}」を{status}にしました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('agents:agent_list')


class AgentCompanyTogglePreferredView(
    LoginRequiredMixin,
    AgentCompanyQuerysetMixin,
    HtmxMixin,
    View
):
    """エージェント会社優先パートナー切り替え"""

    def post(self, request, pk, *args, **kwargs):
        # テナント固有のエージェントのみ切り替え可能
        queryset = AgentCompany.objects.filter(tenant=request.tenant)
        agent = get_object_or_404(queryset, pk=pk)

        agent.is_preferred = not agent.is_preferred
        agent.save(update_fields=['is_preferred', 'updated_at'])

        status = '優先パートナーに設定' if agent.is_preferred else '優先パートナーを解除'
        messages.success(request, f'エージェント「{agent.name}」を{status}しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('agents:agent_detail', pk=agent.pk)


class AgentCompanyUpdateStatsView(
    LoginRequiredMixin,
    AgentCompanyQuerysetMixin,
    HtmxMixin,
    View
):
    """エージェント会社統計更新"""

    def post(self, request, pk, *args, **kwargs):
        queryset = AgentCompany.objects.filter(
            Q(tenant=request.tenant) | Q(tenant__isnull=True)
        )
        agent = get_object_or_404(queryset, pk=pk)

        agent.update_statistics()
        messages.success(request, f'エージェント「{agent.name}」の統計を更新しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('agents:agent_detail', pk=agent.pk)
