"""
Django ATS - 設定ビュー
StatusSetting, ApplicationSource, EmailTemplate のCRUD
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    View,
)

from apps.core.mixins import (
    HtmxMixin,
    TenantQuerysetMixin,
    PaginationMixin,
)
from .models import (
    StatusSetting, ApplicationSource, EmailTemplate,
    StatusCategoryChoices, SourceTypeChoices,
    SpreadsheetConnection,
)
from .forms import (
    StatusSettingForm, StatusSettingFilterForm,
    ApplicationSourceForm, ApplicationSourceFilterForm,
    EmailTemplateForm, EmailTemplateFilterForm,
    SpreadsheetConnectionForm,
)


# =============================================================================
# 設定インデックス
# =============================================================================

class SettingsIndexView(LoginRequiredMixin, HtmxMixin, TemplateView):
    """設定インデックス（タブ付き）"""
    template_name = 'settings/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        # 各設定のサマリー
        context['status_count'] = StatusSetting.objects.filter(
            tenant=tenant
        ).count()
        context['source_count'] = ApplicationSource.objects.filter(
            Q(tenant=tenant) | Q(tenant__isnull=True)
        ).count()
        context['template_count'] = EmailTemplate.objects.filter(
            tenant=tenant
        ).count()

        # スプレッドシート連携情報
        spreadsheet_connection = SpreadsheetConnection.objects.filter(
            tenant=tenant
        ).first()
        context['spreadsheet_connection'] = spreadsheet_connection
        context['has_spreadsheet'] = spreadsheet_connection is not None

        context['status_categories'] = StatusCategoryChoices.choices
        context['source_types'] = SourceTypeChoices.choices
        context['template_types'] = EmailTemplate.TemplateTypeChoices.choices

        return context


# =============================================================================
# StatusSetting CRUD
# =============================================================================

class StatusSettingListView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """ステータス設定一覧"""
    model = StatusSetting
    template_name = 'settings/status/list.html'
    context_object_name = 'statuses'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()

        # カテゴリフィルタ
        category = self.request.GET.get('category')
        if category and category in dict(StatusCategoryChoices.choices):
            queryset = queryset.filter(category=category)

        # 有効フィルタ
        is_active = self.request.GET.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('category', 'display_order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = StatusSettingFilterForm(self.request.GET)
        context['category_choices'] = StatusCategoryChoices.choices
        return context


class StatusSettingCreateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    CreateView
):
    """ステータス設定作成"""
    model = StatusSetting
    form_class = StatusSettingForm
    template_name = 'settings/status/form.html'
    success_url = reverse_lazy('settings:status_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        status = form.save(commit=False)
        status.tenant = self.request.tenant
        status.save()
        messages.success(self.request, f'ステータス「{status.name}」を作成しました。')
        return super().form_valid(form)


class StatusSettingUpdateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """ステータス設定更新"""
    model = StatusSetting
    form_class = StatusSettingForm
    template_name = 'settings/status/form.html'
    success_url = reverse_lazy('settings:status_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'ステータス「{form.instance.name}」を更新しました。')
        return super().form_valid(form)


class StatusSettingDeleteView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    View
):
    """ステータス設定削除"""

    def post(self, request, pk, *args, **kwargs):
        queryset = StatusSetting.objects.filter(tenant=request.tenant)
        status = get_object_or_404(queryset, pk=pk)
        name = status.name
        status.delete()
        messages.success(request, f'ステータス「{name}」を削除しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('settings:status_list')


class StatusSettingReorderView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    View
):
    """ステータス設定並び替え（AJAX）"""

    def post(self, request, *args, **kwargs):
        import json
        try:
            data = json.loads(request.body)
            order = data.get('order', [])

            for index, pk in enumerate(order):
                StatusSetting.objects.filter(
                    pk=pk, tenant=request.tenant
                ).update(display_order=index)

            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# =============================================================================
# ApplicationSource CRUD
# =============================================================================

class ApplicationSourceQuerysetMixin:
    """応募経路のクエリセット制御"""

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            queryset = queryset.filter(
                Q(tenant=tenant) | Q(tenant__isnull=True)
            )
        return queryset


class ApplicationSourceListView(
    LoginRequiredMixin,
    ApplicationSourceQuerysetMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """応募経路一覧"""
    model = ApplicationSource
    template_name = 'settings/sources/list.html'
    context_object_name = 'sources'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()

        # タイプフィルタ
        source_type = self.request.GET.get('source_type')
        if source_type and source_type in dict(SourceTypeChoices.choices):
            queryset = queryset.filter(source_type=source_type)

        # 有効フィルタ
        is_active = self.request.GET.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        # スコープフィルタ
        scope = self.request.GET.get('scope')
        if scope == 'global':
            queryset = queryset.filter(tenant__isnull=True)
        elif scope == 'tenant':
            queryset = queryset.filter(tenant__isnull=False)

        return queryset.order_by('display_order', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ApplicationSourceFilterForm(self.request.GET)
        context['source_type_choices'] = SourceTypeChoices.choices
        return context


class ApplicationSourceCreateView(
    LoginRequiredMixin,
    HtmxMixin,
    CreateView
):
    """応募経路作成"""
    model = ApplicationSource
    form_class = ApplicationSourceForm
    template_name = 'settings/sources/form.html'
    success_url = reverse_lazy('settings:source_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        source = form.save(commit=False)
        source.tenant = self.request.tenant
        source.save()
        messages.success(self.request, f'応募経路「{source.name}」を作成しました。')
        return super().form_valid(form)


class ApplicationSourceUpdateView(
    LoginRequiredMixin,
    ApplicationSourceQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """応募経路更新"""
    model = ApplicationSource
    form_class = ApplicationSourceForm
    template_name = 'settings/sources/form.html'
    success_url = reverse_lazy('settings:source_list')

    def get_queryset(self):
        # テナント固有のみ編集可能
        return ApplicationSource.objects.filter(tenant=self.request.tenant)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'応募経路「{form.instance.name}」を更新しました。')
        return super().form_valid(form)


class ApplicationSourceDeleteView(
    LoginRequiredMixin,
    ApplicationSourceQuerysetMixin,
    HtmxMixin,
    View
):
    """応募経路削除"""

    def post(self, request, pk, *args, **kwargs):
        # テナント固有のみ削除可能
        queryset = ApplicationSource.objects.filter(tenant=request.tenant)
        source = get_object_or_404(queryset, pk=pk)
        name = source.name
        source.delete()
        messages.success(request, f'応募経路「{name}」を削除しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('settings:source_list')


# =============================================================================
# EmailTemplate CRUD
# =============================================================================

class EmailTemplateListView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """メールテンプレート一覧"""
    model = EmailTemplate
    template_name = 'settings/templates/list.html'
    context_object_name = 'templates'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()

        # タイプフィルタ
        template_type = self.request.GET.get('template_type')
        if template_type and template_type in dict(EmailTemplate.TemplateTypeChoices.choices):
            queryset = queryset.filter(template_type=template_type)

        # 有効フィルタ
        is_active = self.request.GET.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('template_type', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = EmailTemplateFilterForm(self.request.GET)
        context['template_type_choices'] = EmailTemplate.TemplateTypeChoices.choices
        return context


class EmailTemplateCreateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    CreateView
):
    """メールテンプレート作成"""
    model = EmailTemplate
    form_class = EmailTemplateForm
    template_name = 'settings/templates/form.html'
    success_url = reverse_lazy('settings:template_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        template = form.save(commit=False)
        template.tenant = self.request.tenant
        template.save()
        messages.success(self.request, f'メールテンプレート「{template.name}」を作成しました。')
        return super().form_valid(form)


class EmailTemplateUpdateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """メールテンプレート更新"""
    model = EmailTemplate
    form_class = EmailTemplateForm
    template_name = 'settings/templates/form.html'
    success_url = reverse_lazy('settings:template_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'メールテンプレート「{form.instance.name}」を更新しました。')
        return super().form_valid(form)


class EmailTemplateDeleteView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    View
):
    """メールテンプレート削除"""

    def post(self, request, pk, *args, **kwargs):
        queryset = EmailTemplate.objects.filter(tenant=request.tenant)
        template = get_object_or_404(queryset, pk=pk)
        name = template.name
        template.delete()
        messages.success(request, f'メールテンプレート「{name}」を削除しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('settings:template_list')


class EmailTemplatePreviewView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """メールテンプレートプレビュー"""
    model = EmailTemplate
    template_name = 'settings/templates/preview.html'
    context_object_name = 'template'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # サンプルデータでレンダリング
        sample_context = {
            'candidate_name': '山田 太郎',
            'job_title': 'シニアエンジニア',
            'company_name': 'サンプル株式会社',
            'interview_date': '2025年1月15日 14:00',
            'interviewer_name': '鈴木 花子',
            'offer_amount': '800万円',
        }
        rendered = self.object.render(sample_context)
        context['preview_subject'] = rendered['subject']
        context['preview_body'] = rendered['body']
        context['sample_context'] = sample_context

        return context


class EmailTemplateDuplicateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    View
):
    """メールテンプレート複製"""

    def post(self, request, pk, *args, **kwargs):
        queryset = EmailTemplate.objects.filter(tenant=request.tenant)
        template = get_object_or_404(queryset, pk=pk)

        # 複製を作成
        new_template = EmailTemplate.objects.get(pk=pk)
        new_template.pk = None
        new_template.name = f"{template.name} (コピー)"
        new_template.is_default = False
        new_template.save()

        messages.success(request, f'メールテンプレート「{template.name}」を複製しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('settings:template_list')


# =============================================================================
# SpreadsheetConnection CRUD
# =============================================================================

class SpreadsheetConnectionDetailView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """スプレッドシート連携詳細"""
    model = SpreadsheetConnection
    template_name = 'settings/spreadsheet/detail.html'
    context_object_name = 'connection'

    def get_object(self):
        """テナントの連携設定を取得（なければ404）"""
        return get_object_or_404(
            SpreadsheetConnection,
            tenant=self.request.tenant
        )


class SpreadsheetConnectionCreateView(
    LoginRequiredMixin,
    HtmxMixin,
    CreateView
):
    """スプレッドシート連携作成"""
    model = SpreadsheetConnection
    form_class = SpreadsheetConnectionForm
    template_name = 'settings/spreadsheet/form.html'
    success_url = '/settings/spreadsheet/'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        connection = form.save(commit=False)
        connection.tenant = self.request.tenant
        connection.save()

        # 接続テスト
        try:
            from apps.core.services import SpreadsheetSyncService
            service = SpreadsheetSyncService(connection)
            success, message = service.test_connection()
            if success:
                messages.success(self.request, f'スプレッドシート連携を設定しました。{message}')
            else:
                messages.warning(self.request, f'スプレッドシートに接続できませんでした。{message}')
        except ImportError:
            messages.warning(
                self.request,
                'スプレッドシート連携に必要なライブラリ（gspread, google-auth）がインストールされていません。'
            )
        except Exception as e:
            messages.warning(self.request, f'接続テストに失敗しました: {e}')

        return redirect(self.success_url)


class SpreadsheetConnectionUpdateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """スプレッドシート連携更新"""
    model = SpreadsheetConnection
    form_class = SpreadsheetConnectionForm
    template_name = 'settings/spreadsheet/form.html'
    success_url = '/settings/spreadsheet/'

    def get_object(self):
        return get_object_or_404(
            SpreadsheetConnection,
            tenant=self.request.tenant
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'スプレッドシート連携設定を更新しました。')
        return super().form_valid(form)


class SpreadsheetConnectionDeleteView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    View
):
    """スプレッドシート連携削除"""

    def post(self, request, *args, **kwargs):
        connection = get_object_or_404(
            SpreadsheetConnection,
            tenant=request.tenant
        )
        connection.delete()
        messages.success(request, 'スプレッドシート連携を解除しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('settings:index')


class SpreadsheetTestConnectionView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    View
):
    """スプレッドシート接続テスト"""

    def post(self, request, *args, **kwargs):
        connection = get_object_or_404(
            SpreadsheetConnection,
            tenant=request.tenant
        )

        try:
            from apps.core.services import SpreadsheetSyncService
            service = SpreadsheetSyncService(connection)
            success, message = service.test_connection()

            if success:
                messages.success(request, f'接続成功: {message}')
            else:
                messages.error(request, f'接続失敗: {message}')
        except ImportError:
            messages.error(
                request,
                '必要なライブラリ（gspread, google-auth）がインストールされていません。'
            )
        except Exception as e:
            messages.error(request, f'接続テストエラー: {e}')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('settings:spreadsheet_detail')


class SpreadsheetSyncView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    View
):
    """スプレッドシート同期実行"""

    def post(self, request, *args, **kwargs):
        connection = get_object_or_404(
            SpreadsheetConnection,
            tenant=request.tenant
        )
        direction = request.POST.get('direction', 'push')  # push, pull, both

        try:
            from apps.core.services import SpreadsheetSyncService
            service = SpreadsheetSyncService(connection)

            if direction == 'push':
                results = service.push_to_spreadsheet()
                total = sum(results.values())
                messages.success(
                    request,
                    f'アプリ → スプレッドシート同期完了: {total}件反映'
                )
            elif direction == 'pull':
                results = service.pull_from_spreadsheet()
                created = sum(r[0] for r in results.values())
                updated = sum(r[1] for r in results.values())
                messages.success(
                    request,
                    f'スプレッドシート → アプリ同期完了: 新規{created}件、更新{updated}件'
                )
            else:  # both
                results = service.sync_all()
                messages.success(request, '双方向同期完了')

        except ImportError:
            messages.error(
                request,
                '必要なライブラリ（gspread, google-auth）がインストールされていません。'
            )
        except Exception as e:
            messages.error(request, f'同期エラー: {e}')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('settings:spreadsheet_detail')
