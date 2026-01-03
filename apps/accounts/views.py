"""
Django ATS - アカウント関連ビュー
ユーザープロファイル、パスワード変更など
"""

from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordChangeView as BasePasswordChangeView,
    PasswordChangeDoneView as BasePasswordChangeDoneView,
)
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView,
    UpdateView,
    ListView,
    DetailView,
    CreateView,
)
from django.http import HttpResponse

from apps.core.mixins import (
    HtmxMixin,
    TenantQuerysetMixin,
    AdminRequiredMixin,
    PaginationMixin,
    SearchMixin,
)
from apps.core.models import AuditLog
from .models import CustomUser, Profile, UserRoleChoices, LoginHistory
from .forms import ProfileForm, UserCreateForm, UserUpdateForm


class ProfileView(LoginRequiredMixin, HtmxMixin, TemplateView):
    """ユーザープロファイル表示"""
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = getattr(self.request.user, 'profile', None)
        return context


class ProfileUpdateView(LoginRequiredMixin, HtmxMixin, UpdateView):
    """プロファイル更新"""
    model = Profile
    form_class = ProfileForm
    template_name = 'accounts/profile_form.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        # ユーザーのプロファイルを取得または作成
        profile, created = Profile.objects.get_or_create(
            user=self.request.user,
            defaults={'tenant': self.request.user.tenant}
        )
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'プロファイルを更新しました。')
        return super().form_valid(form)


class PasswordChangeView(LoginRequiredMixin, BasePasswordChangeView):
    """パスワード変更"""
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')


class PasswordChangeDoneView(LoginRequiredMixin, BasePasswordChangeDoneView):
    """パスワード変更完了"""
    template_name = 'accounts/password_change_done.html'


class LogoutConfirmView(LoginRequiredMixin, TemplateView):
    """ログアウト確認"""
    template_name = 'accounts/logout_confirm.html'


class LogoutView(LoginRequiredMixin, TemplateView):
    """ログアウト処理"""

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, 'ログアウトしました。')
        return redirect('account_login')


# ===============================
# 管理者用ユーザー管理ビュー
# ===============================

class UserListView(
    AdminRequiredMixin,
    TenantQuerysetMixin,
    SearchMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """ユーザー一覧（管理者用）"""
    model = CustomUser
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    search_fields = ['email', 'first_name', 'last_name']
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        # 同一テナントのユーザーのみ表示
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)

        # ロールでフィルタ
        role = self.request.GET.get('role')
        if role and role in dict(UserRoleChoices.choices):
            queryset = queryset.filter(role=role)

        # アクティブ状態でフィルタ
        is_active = self.request.GET.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')

        return queryset.select_related('tenant', 'profile')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['role_choices'] = UserRoleChoices.choices
        context['selected_role'] = self.request.GET.get('role', '')
        return context


class UserDetailView(
    AdminRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """ユーザー詳細"""
    model = CustomUser
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset.select_related('tenant', 'profile')


class UserCreateView(
    AdminRequiredMixin,
    HtmxMixin,
    CreateView
):
    """ユーザー作成"""
    model = CustomUser
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        user = form.save(commit=False)
        user.tenant = self.request.tenant
        user.save()
        messages.success(self.request, f'ユーザー "{user.email}" を作成しました。')
        return super().form_valid(form)


class UserUpdateView(
    AdminRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """ユーザー更新"""
    model = CustomUser
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset

    def form_valid(self, form):
        messages.success(self.request, f'ユーザー "{form.instance.email}" を更新しました。')
        return super().form_valid(form)


class UserToggleActiveView(
    AdminRequiredMixin,
    HtmxMixin,
    TemplateView
):
    """ユーザー有効/無効切り替え"""

    def post(self, request, pk, *args, **kwargs):
        queryset = CustomUser.objects.all()
        if request.tenant:
            queryset = queryset.filter(tenant=request.tenant)

        user = get_object_or_404(queryset, pk=pk)

        # 自分自身は無効化できない
        if user == request.user:
            messages.error(request, '自分自身を無効化することはできません。')
            return redirect('accounts:user_list')

        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])

        status = '有効' if user.is_active else '無効'
        messages.success(request, f'ユーザー "{user.email}" を{status}にしました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('accounts:user_list')


# ===============================
# システム管理者用テナント切り替え
# ===============================

class TenantSwitchView(LoginRequiredMixin, TemplateView):
    """テナント切り替え（システム管理者用）"""
    template_name = 'accounts/tenant_switch.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.is_system_admin:
            messages.error(request, 'システム管理者のみがテナント切り替えを行えます。')
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.tenants.models import Tenant
        context['tenants'] = Tenant.objects.filter(is_active=True).order_by('name')
        context['current_tenant_id'] = self.request.session.get('selected_tenant_id')
        return context

    def post(self, request, *args, **kwargs):
        tenant_id = request.POST.get('tenant_id')
        if tenant_id:
            from apps.tenants.models import Tenant
            try:
                tenant = Tenant.objects.get(id=tenant_id, is_active=True)
                request.session['selected_tenant_id'] = str(tenant.id)
                messages.success(request, f'テナント "{tenant.name}" に切り替えました。')
            except Tenant.DoesNotExist:
                messages.error(request, '指定されたテナントが見つかりません。')
        else:
            # テナント選択解除
            if 'selected_tenant_id' in request.session:
                del request.session['selected_tenant_id']
            messages.info(request, 'テナント選択を解除しました。')

        return redirect('accounts:tenant_switch')


# ===============================
# 監査ログ・ログイン履歴ビュー
# ===============================

class AuditLogListView(
    AdminRequiredMixin,
    TenantQuerysetMixin,
    SearchMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """監査ログ一覧

    テナント内のすべての操作履歴を表示。
    コンサルタント・人事担当者以上のみアクセス可能。
    """
    model = AuditLog
    template_name = 'accounts/audit_log_list.html'
    context_object_name = 'logs'
    search_fields = ['object_repr', 'user__email']
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)

        # アクションでフィルタ
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)

        # モデルでフィルタ
        model_name = self.request.GET.get('model')
        if model_name:
            queryset = queryset.filter(resource_type=model_name)

        # ユーザーでフィルタ
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # 日付範囲でフィルタ
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)

        return queryset.select_related('user', 'tenant').order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.models import AuditActionChoices

        context['action_choices'] = AuditActionChoices.choices
        context['model_names'] = (
            AuditLog.objects.filter(tenant=self.request.tenant)
            .values_list('resource_type', flat=True)
            .distinct()
            .order_by('resource_type')
        ) if self.request.tenant else []
        context['users'] = (
            CustomUser.objects.filter(tenant=self.request.tenant)
            .values('id', 'email')
            .order_by('email')
        ) if self.request.tenant else []

        # 選択中のフィルタ
        context['selected_action'] = self.request.GET.get('action', '')
        context['selected_model'] = self.request.GET.get('model', '')
        context['selected_user'] = self.request.GET.get('user', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')

        return context


class AuditLogDetailView(
    AdminRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """監査ログ詳細"""
    model = AuditLog
    template_name = 'accounts/audit_log_detail.html'
    context_object_name = 'log'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset.select_related('user', 'tenant')


class LoginHistoryListView(
    AdminRequiredMixin,
    TenantQuerysetMixin,
    SearchMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """ログイン履歴一覧

    ユーザーのログイン試行履歴を表示。
    成功・失敗を含む全ての試行を記録。
    """
    model = LoginHistory
    template_name = 'accounts/login_history_list.html'
    context_object_name = 'histories'
    search_fields = ['email_attempted', 'ip_address']
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()

        # テナント内ユーザーのみ（テナントが設定されている場合）
        if self.request.tenant:
            queryset = queryset.filter(user__tenant=self.request.tenant)

        # 成功/失敗でフィルタ
        success = self.request.GET.get('success')
        if success == 'true':
            queryset = queryset.filter(success=True)
        elif success == 'false':
            queryset = queryset.filter(success=False)

        # ユーザーでフィルタ
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # 日付範囲でフィルタ
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)

        return queryset.select_related('user').order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['users'] = (
            CustomUser.objects.filter(tenant=self.request.tenant)
            .values('id', 'email')
            .order_by('email')
        ) if self.request.tenant else []

        # 選択中のフィルタ
        context['selected_success'] = self.request.GET.get('success', '')
        context['selected_user'] = self.request.GET.get('user', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')

        # サマリー統計
        if self.request.tenant:
            from django.utils import timezone
            from datetime import timedelta

            now = timezone.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)

            base_qs = LoginHistory.objects.filter(user__tenant=self.request.tenant)

            context['stats'] = {
                'total_24h': base_qs.filter(timestamp__gte=last_24h).count(),
                'failed_24h': base_qs.filter(timestamp__gte=last_24h, success=False).count(),
                'total_7d': base_qs.filter(timestamp__gte=last_7d).count(),
                'failed_7d': base_qs.filter(timestamp__gte=last_7d, success=False).count(),
            }

        return context


class MyLoginHistoryView(
    LoginRequiredMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """自分のログイン履歴

    現在のユーザーのログイン履歴を表示。
    """
    model = LoginHistory
    template_name = 'accounts/my_login_history.html'
    context_object_name = 'histories'
    paginate_by = 20

    def get_queryset(self):
        return LoginHistory.objects.filter(
            user=self.request.user
        ).order_by('-timestamp')
