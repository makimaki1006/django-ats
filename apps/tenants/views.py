"""Django ATS - Tenants ビュー

テナント（顧客企業）管理用ビュー。
システム管理者のみがアクセス可能。

機能:
1. テナント一覧 - すべてのテナントを一覧表示
2. テナント詳細 - 統計情報、ユーザー一覧
3. テナント作成/編集
4. テナント有効/無効切り替え
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
)

from apps.core.mixins import HtmxMixin, PaginationMixin, SearchMixin
from apps.tenants.models import Tenant, TenantSpreadsheet
from apps.tenants.forms import TenantForm, TenantSpreadsheetForm


class ConsultingStaffRequiredMixin:
    """御社スタッフ（システム管理者・コンサルタント）専用ミックスイン

    SYSTEM_ADMIN または CONSULTANT ロールのユーザーのみアクセス可能。
    顧客企業（テナント）のユーザーはアクセス不可。
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        # システム管理者またはコンサルタントのみ許可
        if not (request.user.is_system_admin or request.user.is_consultant):
            return HttpResponseForbidden('この機能は管理者・コンサルタントのみ利用可能です。')
        return super().dispatch(request, *args, **kwargs)


# 後方互換性のためエイリアスを維持
SuperuserRequiredMixin = ConsultingStaffRequiredMixin


class TenantListView(SuperuserRequiredMixin, HtmxMixin, SearchMixin, PaginationMixin, ListView):
    """テナント一覧ビュー

    すべてのテナントを一覧表示。
    検索・フィルター・ページネーション対応。
    """
    model = Tenant
    template_name = 'tenants/tenant_list.html'
    htmx_template = 'tenants/partials/tenant_table.html'
    context_object_name = 'tenants'
    paginate_by = 20
    search_fields = ['name', 'code']

    def get_queryset(self):
        # SearchMixinが検索を適用
        qs = super().get_queryset()

        # フィルター: is_active
        is_active = self.request.GET.get('is_active')
        if is_active == 'true':
            qs = qs.filter(is_active=True)
        elif is_active == 'false':
            qs = qs.filter(is_active=False)

        # フィルター: plan
        plan = self.request.GET.get('plan')
        if plan:
            qs = qs.filter(plan=plan)

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plan_choices'] = Tenant.PlanChoices.choices

        # 統計情報
        context['total_tenants'] = Tenant.objects.count()
        context['active_tenants'] = Tenant.objects.filter(is_active=True).count()
        context['inactive_tenants'] = Tenant.objects.filter(is_active=False).count()

        return context


class TenantDetailView(SuperuserRequiredMixin, DetailView):
    """テナント詳細ビュー

    テナント情報、ユーザー一覧、統計情報を表示。
    """
    model = Tenant
    template_name = 'tenants/tenant_detail.html'
    context_object_name = 'tenant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.object

        # ユーザー一覧
        context['users'] = tenant.users.all().order_by('-date_joined')[:10]
        context['total_users'] = tenant.users.count()

        # 統計情報
        from apps.jobs.models import Job
        from apps.candidates.models import Candidate
        from apps.applications.models import Application
        from apps.interviews.models import Interview

        context['stats'] = {
            'jobs': Job.objects.filter(tenant=tenant).count(),
            'active_jobs': Job.objects.filter(tenant=tenant, status='published').count(),
            'candidates': Candidate.objects.filter(tenant=tenant).count(),
            'applications': Application.objects.filter(tenant=tenant).count(),
            'interviews': Interview.objects.filter(tenant=tenant).count(),
        }

        # スプレッドシート接続
        context['spreadsheet'] = getattr(tenant, 'spreadsheet', None)

        return context


class TenantCreateView(SuperuserRequiredMixin, CreateView):
    """テナント作成ビュー"""
    model = Tenant
    form_class = TenantForm
    template_name = 'tenants/tenant_form.html'
    success_url = reverse_lazy('tenants:tenant_list')

    def form_valid(self, form):
        messages.success(self.request, f'テナント「{form.instance.name}」を作成しました。')
        return super().form_valid(form)


class TenantUpdateView(SuperuserRequiredMixin, UpdateView):
    """テナント編集ビュー"""
    model = Tenant
    form_class = TenantForm
    template_name = 'tenants/tenant_form.html'

    def get_success_url(self):
        return reverse_lazy('tenants:tenant_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'テナント「{form.instance.name}」を更新しました。')
        return super().form_valid(form)


class TenantToggleActiveView(SuperuserRequiredMixin, View):
    """テナント有効/無効切り替えビュー（HTMX対応）"""

    def post(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)

        # 切り替え
        tenant.is_active = not tenant.is_active
        tenant.save()

        status_text = '有効' if tenant.is_active else '無効'
        messages.success(request, f'テナント「{tenant.name}」を{status_text}にしました。')

        # HTMXリクエストの場合
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={
                'HX-Trigger': 'tenantUpdated'
            })

        return redirect('tenants:tenant_detail', pk=pk)


class TenantStatsView(SuperuserRequiredMixin, HtmxMixin, View):
    """テナント統計情報ビュー（HTMX対応）"""

    def get(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)

        from apps.jobs.models import Job
        from apps.candidates.models import Candidate
        from apps.applications.models import Application
        from apps.interviews.models import Interview

        stats = {
            'users': tenant.users.count(),
            'max_users': tenant.max_users,
            'jobs': Job.objects.filter(tenant=tenant).count(),
            'candidates': Candidate.objects.filter(tenant=tenant).count(),
            'applications': Application.objects.filter(tenant=tenant).count(),
            'interviews': Interview.objects.filter(tenant=tenant).count(),
        }

        from django.template.loader import render_to_string
        html = render_to_string('tenants/partials/tenant_stats.html', {
            'tenant': tenant,
            'stats': stats,
        })

        return HttpResponse(html)


# スプレッドシート接続管理

class TenantSpreadsheetUpdateView(SuperuserRequiredMixin, View):
    """スプレッドシート接続設定ビュー"""

    def get(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        spreadsheet = getattr(tenant, 'spreadsheet', None)

        form = TenantSpreadsheetForm(instance=spreadsheet)

        from django.template.loader import render_to_string
        html = render_to_string('tenants/partials/spreadsheet_form.html', {
            'tenant': tenant,
            'form': form,
            'spreadsheet': spreadsheet,
        })

        return HttpResponse(html)

    def post(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        spreadsheet = getattr(tenant, 'spreadsheet', None)

        form = TenantSpreadsheetForm(request.POST, instance=spreadsheet)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.tenant = tenant
            instance.save()
            messages.success(request, 'スプレッドシート設定を保存しました。')

            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={
                    'HX-Trigger': 'spreadsheetUpdated'
                })

            return redirect('tenants:tenant_detail', pk=pk)

        from django.template.loader import render_to_string
        html = render_to_string('tenants/partials/spreadsheet_form.html', {
            'tenant': tenant,
            'form': form,
            'spreadsheet': spreadsheet,
        })

        return HttpResponse(html)


class TenantSpreadsheetDeleteView(SuperuserRequiredMixin, View):
    """スプレッドシート接続削除ビュー"""

    def post(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        spreadsheet = getattr(tenant, 'spreadsheet', None)

        if spreadsheet:
            spreadsheet.delete()
            messages.success(request, 'スプレッドシート接続を削除しました。')

        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={
                'HX-Trigger': 'spreadsheetDeleted'
            })

        return redirect('tenants:tenant_detail', pk=pk)


class TenantSpreadsheetSyncView(SuperuserRequiredMixin, View):
    """スプレッドシート同期実行ビュー"""

    def post(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        spreadsheet = getattr(tenant, 'spreadsheet', None)

        if not spreadsheet:
            messages.error(request, 'スプレッドシートが設定されていません。')
            return redirect('tenants:tenant_detail', pk=pk)

        if not spreadsheet.is_active:
            messages.error(request, 'スプレッドシート接続が無効になっています。')
            return redirect('tenants:tenant_detail', pk=pk)

        try:
            from apps.tenants.services import SpreadsheetSyncService

            service = SpreadsheetSyncService(spreadsheet)
            result = service.sync_all()

            if result['success']:
                details = result.get('details', {})
                messages.success(
                    request,
                    f'スプレッドシートを同期しました。'
                    f'（候補者: {details.get("candidates", {}).get("count", 0)}件、'
                    f'応募: {details.get("applications", {}).get("count", 0)}件、'
                    f'面接: {details.get("interviews", {}).get("count", 0)}件）'
                )
            else:
                messages.error(request, f'同期に失敗しました: {result.get("error", "不明なエラー")}')

        except Exception as e:
            messages.error(request, f'同期中にエラーが発生しました: {e}')

        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={
                'HX-Trigger': 'spreadsheetSynced'
            })

        return redirect('tenants:tenant_detail', pk=pk)


class TenantSpreadsheetStatusView(SuperuserRequiredMixin, View):
    """スプレッドシート同期ステータスビュー（HTMX対応）"""

    def get(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        spreadsheet = getattr(tenant, 'spreadsheet', None)

        from django.template.loader import render_to_string
        html = render_to_string('tenants/partials/spreadsheet_status.html', {
            'tenant': tenant,
            'spreadsheet': spreadsheet,
        })

        return HttpResponse(html)
