"""Django ATS - View Mixins

ビュー用のミックスインクラスを提供。
認証、権限、テナント分離、楽観的ロックなどを実装。
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect

from .exceptions import TenantAccessError, RolePermissionError


class TenantQuerysetMixin:
    """テナントでクエリセットをフィルタするミックスイン

    get_queryset() をオーバーライドし、
    現在のユーザーのテナントに属するデータのみを返す。

    Usage:
        class CandidateListView(TenantQuerysetMixin, ListView):
            model = Candidate
    """

    def get_queryset(self):
        """テナントでフィルタしたクエリセットを返す"""
        queryset = super().get_queryset()
        user = self.request.user

        # system_admin は全テナントにアクセス可能
        if hasattr(user, 'role') and user.role == 'system_admin':
            return queryset

        # テナントフィルタを適用
        if hasattr(queryset.model, 'tenant'):
            return queryset.filter(tenant_id=self.request.tenant_id)

        return queryset


class TenantAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """テナントアクセス制御ミックスイン

    オブジェクトが現在のテナントに属することを検証。
    詳細ビュー、編集ビュー、削除ビューで使用。

    Usage:
        class CandidateDetailView(TenantAccessMixin, DetailView):
            model = Candidate
    """

    def test_func(self):
        """テナントアクセス権限をチェック"""
        user = self.request.user

        # system_admin は全テナントにアクセス可能
        if hasattr(user, 'role') and user.role == 'system_admin':
            return True

        # オブジェクトのテナントと現在のテナントを比較
        obj = self.get_object()
        if hasattr(obj, 'tenant_id'):
            return obj.tenant_id == self.request.tenant_id

        return True

    def handle_no_permission(self):
        """権限なし時の処理"""
        if self.request.user.is_authenticated:
            raise TenantAccessError()
        return super().handle_no_permission()


class TenantCreateMixin:
    """テナント自動設定ミックスイン（作成用）

    フォーム保存時に自動的にテナントを設定。
    CreateViewで使用。

    Usage:
        class CandidateCreateView(TenantCreateMixin, CreateView):
            model = Candidate
            form_class = CandidateForm
    """

    def form_valid(self, form):
        """保存前にテナントを設定"""
        if hasattr(form.instance, 'tenant_id'):
            form.instance.tenant_id = self.request.tenant_id

        # 作成者を設定（モデルにフィールドがある場合）
        if hasattr(form.instance, 'created_by_id') and not form.instance.created_by_id:
            form.instance.created_by_id = self.request.user.id

        return super().form_valid(form)


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """ロール権限チェックミックスイン

    指定されたロールを持つユーザーのみアクセス可能。

    Attributes:
        required_roles: 必要なロールのリスト

    Usage:
        class UserManagementView(RoleRequiredMixin, ListView):
            required_roles = ['system_admin', 'client_admin']
    """
    required_roles = []

    def test_func(self):
        """ロール権限をチェック"""
        user = self.request.user
        if not hasattr(user, 'role'):
            return False
        return user.role in self.required_roles

    def handle_no_permission(self):
        """権限なし時の処理"""
        if self.request.user.is_authenticated:
            raise RolePermissionError(required_roles=self.required_roles)
        return super().handle_no_permission()


class AdminRequiredMixin(RoleRequiredMixin):
    """管理者権限チェックミックスイン

    system_admin または client_admin のみアクセス可能。
    """
    required_roles = ['system_admin', 'client_admin']


class SystemAdminRequiredMixin(RoleRequiredMixin):
    """システム管理者権限チェックミックスイン

    system_admin のみアクセス可能。
    """
    required_roles = ['system_admin']


class RecruiterOrAboveMixin(RoleRequiredMixin):
    """採用担当者以上権限チェックミックスイン

    system_admin, client_admin, client_recruiter がアクセス可能。
    """
    required_roles = ['system_admin', 'client_admin', 'client_recruiter']


class ConsultantOrAboveMixin(RoleRequiredMixin):
    """コンサルタント以上権限チェックミックスイン

    採用コンサルタント、人事担当者、システム管理者がアクセス可能。
    """
    required_roles = ['system_admin', 'consultant', 'client_admin', 'hiring_manager']


class HiringManagerOrAboveMixin(RoleRequiredMixin):
    """採用責任者以上権限チェックミックスイン

    採用責任者、人事担当者、システム管理者がアクセス可能。
    """
    required_roles = ['system_admin', 'client_admin', 'hiring_manager']


class FullCandidateAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """候補者情報フルアクセスミックスイン

    候補者情報の全項目にアクセス可能なロールのみ許可。
    - system_admin
    - consultant
    - client_admin
    - hiring_manager
    """

    def test_func(self):
        """候補者フルアクセス権限をチェック"""
        user = self.request.user
        if hasattr(user, 'has_full_candidate_access'):
            return user.has_full_candidate_access
        return False

    def handle_no_permission(self):
        """権限なし時の処理"""
        if self.request.user.is_authenticated:
            raise RolePermissionError(
                message="候補者情報へのアクセス権限がありません。"
            )
        return super().handle_no_permission()


class LimitedCandidateAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """候補者情報限定アクセスミックスイン

    候補者情報への限定的アクセスを持つロールを許可。
    面接官とエージェントは担当分のみアクセス可能。
    """

    def test_func(self):
        """候補者アクセス権限をチェック（フルまたは限定）"""
        user = self.request.user
        # フルアクセスまたは限定アクセスがあれば許可
        if hasattr(user, 'has_full_candidate_access') and user.has_full_candidate_access:
            return True
        if hasattr(user, 'has_limited_candidate_access') and user.has_limited_candidate_access:
            return True
        return False

    def handle_no_permission(self):
        """権限なし時の処理"""
        if self.request.user.is_authenticated:
            raise RolePermissionError(
                message="候補者情報へのアクセス権限がありません。"
            )
        return super().handle_no_permission()


class CandidateQuerysetFilterMixin:
    """候補者クエリセットをロールに応じてフィルタするミックスイン

    ユーザーのロールに基づいて、アクセス可能な候補者のみを返す。

    Usage:
        class CandidateListView(CandidateQuerysetFilterMixin, ListView):
            model = Candidate
    """

    def get_queryset(self):
        """ロールに応じてフィルタしたクエリセットを返す"""
        from apps.candidates.models import Candidate

        queryset = super().get_queryset()
        user = self.request.user

        # Candidateモデルの場合のみロールベースフィルタを適用
        if hasattr(queryset.model, '__name__') and queryset.model.__name__ == 'Candidate':
            # カスタムマネージャーのfor_userメソッドを使用
            return Candidate.objects.for_user(user)

        return queryset


class OptimisticLockMixin:
    """楽観的ロックミックスイン

    同時編集を検出し、コンフリクト時にエラーを表示。
    UpdateViewで使用。

    設計ポイント:
        - フォームにhiddenフィールドとしてversionを含める
        - 保存時にDBの現在のversionと比較
        - 不一致ならエラーメッセージを表示し、再読み込みを促す

    Usage:
        class CandidateUpdateView(OptimisticLockMixin, UpdateView):
            model = Candidate
            form_class = CandidateForm
    """

    def get_initial(self):
        """初期値にversionを含める"""
        initial = super().get_initial()
        if hasattr(self, 'object') and self.object and hasattr(self.object, 'version'):
            initial['version'] = self.object.version
        return initial

    def form_valid(self, form):
        """保存前にバージョンをチェック"""
        obj = form.instance

        if hasattr(obj, 'version') and obj.pk:
            # DBから現在のバージョンを取得
            current_obj = self.get_object()
            current_version = current_obj.version

            # フォームから送信されたバージョンを取得
            submitted_version = form.cleaned_data.get('version', obj.version)

            # バージョン不一致ならエラー
            if submitted_version != current_version:
                messages.error(
                    self.request,
                    "このレコードは他のユーザーによって更新されました。"
                    "ページを再読み込みして、再度編集してください。"
                )
                return redirect(current_obj.get_absolute_url())

        return super().form_valid(form)


class AuditMixin:
    """監査フィールド自動設定ミックスイン

    created_by, updated_by を自動設定。

    Usage:
        class CandidateCreateView(AuditMixin, CreateView):
            model = Candidate
    """

    def form_valid(self, form):
        """保存前に監査フィールドを設定"""
        obj = form.instance
        user = self.request.user

        # 新規作成時
        if not obj.pk:
            if hasattr(obj, 'created_by_id') and not obj.created_by_id:
                obj.created_by_id = user.id

        # 更新時
        if hasattr(obj, 'updated_by_id'):
            obj.updated_by_id = user.id

        return super().form_valid(form)


class SuccessMessageMixin:
    """成功メッセージミックスイン

    操作成功時にメッセージを表示。

    Attributes:
        success_message: 表示するメッセージ

    Usage:
        class CandidateCreateView(SuccessMessageMixin, CreateView):
            success_message = "候補者を登録しました。"
    """
    success_message = None

    def form_valid(self, form):
        """保存成功時にメッセージを追加"""
        response = super().form_valid(form)
        if self.success_message:
            message = self.success_message
            # オブジェクトの属性を埋め込み可能
            if hasattr(self, 'object') and self.object:
                try:
                    message = message.format(object=self.object)
                except (KeyError, AttributeError):
                    pass
            messages.success(self.request, message)
        return response


class HtmxMixin:
    """htmxリクエスト対応ミックスイン

    htmxリクエストの場合は部分テンプレートを返す。

    Attributes:
        htmx_template_name: htmxリクエスト用テンプレート

    Usage:
        class CandidateListView(HtmxMixin, ListView):
            template_name = 'candidates/list.html'
            htmx_template_name = 'candidates/partials/list_content.html'
    """
    htmx_template_name = None

    def get_template_names(self):
        """htmxリクエストなら部分テンプレートを返す"""
        if self.htmx_template_name and getattr(self.request, 'htmx', False):
            return [self.htmx_template_name]
        return super().get_template_names()


class SearchMixin:
    """検索機能ミックスイン

    検索クエリでクエリセットをフィルタ。

    Attributes:
        search_fields: 検索対象フィールド（リスト）

    Usage:
        class CandidateListView(SearchMixin, ListView):
            search_fields = ['name', 'email', 'phone']
    """
    search_fields = []
    search_param = 'q'

    def get_queryset(self):
        """検索フィルタを適用"""
        queryset = super().get_queryset()
        query = self.request.GET.get(self.search_param, '').strip()

        if query and self.search_fields:
            from django.db.models import Q
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f'{field}__icontains': query})
            queryset = queryset.filter(q_objects)

        return queryset

    def get_context_data(self, **kwargs):
        """検索クエリをコンテキストに追加"""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get(self.search_param, '')
        return context


class OrderingMixin:
    """ソート機能ミックスイン

    クエリパラメータでソート順を制御。

    Attributes:
        ordering_fields: ソート可能フィールド（リスト）
        default_ordering: デフォルトのソート順

    Usage:
        class CandidateListView(OrderingMixin, ListView):
            ordering_fields = ['name', 'created_at', 'email']
            default_ordering = '-created_at'
    """
    ordering_fields = []
    default_ordering = '-created_at'
    ordering_param = 'sort'

    def get_ordering(self):
        """リクエストからソート順を取得"""
        sort = self.request.GET.get(self.ordering_param, '')

        if sort:
            # マイナス記号を除去してフィールド名を取得
            field = sort.lstrip('-')
            if field in self.ordering_fields:
                return sort

        return self.default_ordering

    def get_context_data(self, **kwargs):
        """現在のソート順をコンテキストに追加"""
        context = super().get_context_data(**kwargs)
        context['current_sort'] = self.request.GET.get(self.ordering_param, self.default_ordering)
        context['ordering_fields'] = self.ordering_fields
        return context


class PaginationMixin:
    """ページネーション拡張ミックスイン

    ページサイズの動的変更と、コンテキストへの追加情報。

    Attributes:
        page_size_param: ページサイズのクエリパラメータ名
        page_sizes: 選択可能なページサイズ
    """
    paginate_by = 25
    page_size_param = 'per_page'
    page_sizes = [10, 25, 50, 100]

    def get_paginate_by(self, queryset):
        """リクエストからページサイズを取得"""
        per_page = self.request.GET.get(self.page_size_param)
        if per_page and per_page.isdigit():
            per_page = int(per_page)
            if per_page in self.page_sizes:
                return per_page
        return self.paginate_by

    def get_context_data(self, **kwargs):
        """ページネーション情報をコンテキストに追加"""
        context = super().get_context_data(**kwargs)
        context['page_sizes'] = self.page_sizes
        context['current_page_size'] = self.get_paginate_by(self.get_queryset())
        return context
