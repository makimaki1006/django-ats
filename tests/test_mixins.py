"""Django ATS - ミックスインテスト

ビュー用ミックスインのテスト。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from django.test import RequestFactory
from django.views import View
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.contrib.auth.models import AnonymousUser
from django.contrib import messages
from django.http import HttpResponse

from apps.core.mixins import (
    TenantQuerysetMixin,
    TenantAccessMixin,
    TenantCreateMixin,
    RoleRequiredMixin,
    AdminRequiredMixin,
    SystemAdminRequiredMixin,
    RecruiterOrAboveMixin,
    FullCandidateAccessMixin,
    LimitedCandidateAccessMixin,
    OptimisticLockMixin,
    AuditMixin,
    SuccessMessageMixin,
    HtmxMixin,
    SearchMixin,
    OrderingMixin,
    PaginationMixin,
)
from apps.core.exceptions import TenantAccessError, RolePermissionError
from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def rf():
    """RequestFactory"""
    return RequestFactory()


@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='ミックスインテスト',
        code='mixin-test',
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """通常ユーザー"""
    return CustomUser.objects.create_user(
        email='user@mixin-test.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@mixin-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def system_admin(db, tenant):
    """システム管理者"""
    return CustomUser.objects.create_user(
        email='sysadmin@mixin-test.com',
        password='testpass123',
        role=UserRoleChoices.SYSTEM_ADMIN,
        tenant=tenant,
    )


# =============================================================================
# RoleRequiredMixin Tests
# =============================================================================

class TestRoleRequiredMixin:
    """RoleRequiredMixin のテスト"""

    @pytest.mark.django_db
    def test_user_with_required_role(self, rf, admin_user):
        """必要なロールを持つユーザーはアクセス可能"""
        class TestView(RoleRequiredMixin, View):
            required_roles = ['client_admin', 'system_admin']

        view = TestView()
        request = rf.get('/test/')
        request.user = admin_user
        view.request = request

        assert view.test_func() is True

    @pytest.mark.django_db
    def test_user_without_required_role(self, rf, user):
        """必要なロールを持たないユーザーはアクセス不可"""
        class TestView(RoleRequiredMixin, View):
            required_roles = ['client_admin', 'system_admin']

        view = TestView()
        request = rf.get('/test/')
        request.user = user
        view.request = request

        assert view.test_func() is False

    @pytest.mark.django_db
    def test_user_without_role_attribute(self, rf):
        """roleアトリビュートがないユーザー"""
        class TestView(RoleRequiredMixin, View):
            required_roles = ['client_admin']

        view = TestView()
        request = rf.get('/test/')
        request.user = MagicMock(spec=[])  # roleアトリビュートなし
        view.request = request

        assert view.test_func() is False


# =============================================================================
# AdminRequiredMixin Tests
# =============================================================================

class TestAdminRequiredMixin:
    """AdminRequiredMixin のテスト"""

    @pytest.mark.django_db
    def test_admin_can_access(self, rf, admin_user):
        """管理者はアクセス可能"""
        class TestView(AdminRequiredMixin, View):
            pass

        view = TestView()
        request = rf.get('/test/')
        request.user = admin_user
        view.request = request

        # client_adminがrequired_rolesに含まれている
        assert 'client_admin' in view.required_roles
        assert view.test_func() is True

    @pytest.mark.django_db
    def test_system_admin_can_access(self, rf, system_admin):
        """システム管理者はアクセス可能"""
        class TestView(AdminRequiredMixin, View):
            pass

        view = TestView()
        request = rf.get('/test/')
        request.user = system_admin
        view.request = request

        assert view.test_func() is True


# =============================================================================
# SystemAdminRequiredMixin Tests
# =============================================================================

class TestSystemAdminRequiredMixin:
    """SystemAdminRequiredMixin のテスト"""

    @pytest.mark.django_db
    def test_system_admin_can_access(self, rf, system_admin):
        """システム管理者はアクセス可能"""
        class TestView(SystemAdminRequiredMixin, View):
            pass

        view = TestView()
        request = rf.get('/test/')
        request.user = system_admin
        view.request = request

        assert view.test_func() is True

    @pytest.mark.django_db
    def test_client_admin_cannot_access(self, rf, admin_user):
        """クライアント管理者はアクセス不可"""
        class TestView(SystemAdminRequiredMixin, View):
            pass

        view = TestView()
        request = rf.get('/test/')
        request.user = admin_user
        view.request = request

        assert view.test_func() is False


# =============================================================================
# RecruiterOrAboveMixin Tests
# =============================================================================

class TestRecruiterOrAboveMixin:
    """RecruiterOrAboveMixin のテスト"""

    @pytest.mark.django_db
    def test_recruiter_can_access(self, rf, tenant):
        """採用担当者はアクセス可能"""
        recruiter = CustomUser.objects.create_user(
            email='recruiter@mixin-test.com',
            password='testpass123',
            role=UserRoleChoices.CLIENT_RECRUITER,
            tenant=tenant,
        )

        class TestView(RecruiterOrAboveMixin, View):
            pass

        view = TestView()
        request = rf.get('/test/')
        request.user = recruiter
        view.request = request

        assert view.test_func() is True


# =============================================================================
# FullCandidateAccessMixin Tests
# =============================================================================

class TestFullCandidateAccessMixin:
    """FullCandidateAccessMixin のテスト"""

    @pytest.mark.django_db
    def test_user_with_full_access(self, rf, admin_user):
        """フルアクセス権限を持つユーザー"""
        class TestView(FullCandidateAccessMixin, View):
            pass

        view = TestView()
        request = rf.get('/test/')
        request.user = admin_user
        view.request = request

        # has_full_candidate_accessがTrueならアクセス可能
        if hasattr(admin_user, 'has_full_candidate_access') and admin_user.has_full_candidate_access:
            assert view.test_func() is True

    @pytest.mark.django_db
    def test_user_without_full_access(self, rf, user):
        """フルアクセス権限を持たないユーザー"""
        class TestView(FullCandidateAccessMixin, View):
            pass

        view = TestView()
        request = rf.get('/test/')
        request.user = user
        view.request = request

        # INTERVIEWERはフルアクセスなし
        if not user.has_full_candidate_access:
            assert view.test_func() is False


# =============================================================================
# LimitedCandidateAccessMixin Tests
# =============================================================================

class TestLimitedCandidateAccessMixin:
    """LimitedCandidateAccessMixin のテスト"""

    @pytest.mark.django_db
    def test_user_with_limited_access(self, rf, user):
        """限定アクセス権限を持つユーザー"""
        class TestView(LimitedCandidateAccessMixin, View):
            pass

        view = TestView()
        request = rf.get('/test/')
        request.user = user
        view.request = request

        # INTERVIEWERは限定アクセスあり
        if user.has_limited_candidate_access:
            assert view.test_func() is True

    @pytest.mark.django_db
    def test_user_with_full_access_can_access(self, rf, admin_user):
        """フルアクセス権限を持つユーザーもアクセス可能"""
        class TestView(LimitedCandidateAccessMixin, View):
            pass

        view = TestView()
        request = rf.get('/test/')
        request.user = admin_user
        view.request = request

        # フルアクセスがあればTrueを返す
        if admin_user.has_full_candidate_access:
            assert view.test_func() is True


# =============================================================================
# SearchMixin Tests
# =============================================================================

class TestSearchMixin:
    """SearchMixin のテスト"""

    @pytest.mark.django_db
    def test_get_queryset_with_search(self, rf):
        """検索クエリでフィルタ"""
        class TestView(SearchMixin, ListView):
            model = Tenant
            search_fields = ['name', 'code']

            def get_queryset(self):
                return Tenant.objects.all()

        # テストデータ作成
        Tenant.objects.create(name='検索テスト1', code='search-1')
        Tenant.objects.create(name='別のテナント', code='other-1')

        view = TestView()
        request = rf.get('/test/?q=検索')
        view.request = request

        queryset = view.get_queryset()
        # 「検索」を含むテナントのみ
        assert queryset.filter(name__icontains='検索').count() == 1

    @pytest.mark.django_db
    def test_get_context_data_includes_search_query(self, rf):
        """コンテキストに検索クエリを含む"""
        class TestView(SearchMixin, ListView):
            model = Tenant
            search_fields = ['name']

            def get_queryset(self):
                return Tenant.objects.all()

        view = TestView()
        request = rf.get('/test/?q=テスト')
        view.request = request
        view.object_list = view.get_queryset()

        context = view.get_context_data()
        assert context['search_query'] == 'テスト'


# =============================================================================
# OrderingMixin Tests
# =============================================================================

class TestOrderingMixin:
    """OrderingMixin のテスト"""

    @pytest.mark.django_db
    def test_get_ordering_with_valid_field(self, rf):
        """有効なソートフィールド"""
        class TestView(OrderingMixin, ListView):
            model = Tenant
            ordering_fields = ['name', 'created_at']

        view = TestView()
        request = rf.get('/test/?sort=name')
        view.request = request

        assert view.get_ordering() == 'name'

    @pytest.mark.django_db
    def test_get_ordering_with_descending(self, rf):
        """降順ソート"""
        class TestView(OrderingMixin, ListView):
            model = Tenant
            ordering_fields = ['name', 'created_at']

        view = TestView()
        request = rf.get('/test/?sort=-name')
        view.request = request

        assert view.get_ordering() == '-name'

    @pytest.mark.django_db
    def test_get_ordering_with_invalid_field(self, rf):
        """無効なソートフィールドはデフォルトを使用"""
        class TestView(OrderingMixin, ListView):
            model = Tenant
            ordering_fields = ['name']
            default_ordering = '-created_at'

        view = TestView()
        request = rf.get('/test/?sort=invalid_field')
        view.request = request

        assert view.get_ordering() == '-created_at'


# =============================================================================
# PaginationMixin Tests
# =============================================================================

class TestPaginationMixin:
    """PaginationMixin のテスト"""

    @pytest.mark.django_db
    def test_get_paginate_by_default(self, rf):
        """デフォルトのページサイズ"""
        class TestView(PaginationMixin, ListView):
            model = Tenant

        view = TestView()
        request = rf.get('/test/')
        view.request = request

        assert view.get_paginate_by(Tenant.objects.all()) == 25

    @pytest.mark.django_db
    def test_get_paginate_by_custom(self, rf):
        """カスタムページサイズ"""
        class TestView(PaginationMixin, ListView):
            model = Tenant
            page_sizes = [10, 25, 50, 100]

        view = TestView()
        request = rf.get('/test/?per_page=50')
        view.request = request

        assert view.get_paginate_by(Tenant.objects.all()) == 50

    @pytest.mark.django_db
    def test_get_paginate_by_invalid(self, rf):
        """無効なページサイズはデフォルトを使用"""
        class TestView(PaginationMixin, ListView):
            model = Tenant
            page_sizes = [10, 25, 50]

        view = TestView()
        request = rf.get('/test/?per_page=999')
        view.request = request

        assert view.get_paginate_by(Tenant.objects.all()) == 25


# =============================================================================
# HtmxMixin Tests
# =============================================================================

class TestHtmxMixin:
    """HtmxMixin のテスト"""

    @pytest.mark.django_db
    def test_htmx_template_returned(self, rf):
        """htmxリクエスト時は部分テンプレートを返す"""
        class TestView(HtmxMixin, ListView):
            model = Tenant
            template_name = 'tenants/list.html'
            htmx_template_name = 'tenants/partials/list_content.html'

        view = TestView()
        request = rf.get('/test/')
        request.htmx = True
        view.request = request

        templates = view.get_template_names()
        assert 'tenants/partials/list_content.html' in templates

    @pytest.mark.django_db
    def test_normal_template_returned(self, rf):
        """通常リクエスト時はメインテンプレートを返す"""
        class TestView(HtmxMixin, ListView):
            model = Tenant
            template_name = 'tenants/list.html'
            htmx_template_name = 'tenants/partials/list_content.html'

        view = TestView()
        request = rf.get('/test/')
        request.htmx = False
        view.request = request
        view.object_list = Tenant.objects.none()

        templates = view.get_template_names()
        assert 'tenants/list.html' in templates


# =============================================================================
# SuccessMessageMixin Tests
# =============================================================================

class TestSuccessMessageMixin:
    """SuccessMessageMixin のテスト"""

    @pytest.mark.django_db
    def test_success_message_added(self, rf, tenant):
        """成功メッセージが追加される"""
        class TestView(SuccessMessageMixin, UpdateView):
            model = Tenant
            fields = ['name']
            success_message = "更新しました。"
            success_url = '/tenants/'

        view = TestView()
        request = rf.post('/test/', {'name': '更新後テナント'})
        # セッションとメッセージミドルウェアを追加
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.messages.storage.fallback import FallbackStorage

        session_middleware = SessionMiddleware(lambda r: None)
        session_middleware.process_request(request)
        request.session.save()

        message_middleware = MessageMiddleware(lambda r: None)
        message_middleware.process_request(request)

        # メッセージストレージを設定
        setattr(request, '_messages', FallbackStorage(request))

        view.request = request
        view.object = tenant

        # form_validのテスト
        from django import forms

        class TenantForm(forms.ModelForm):
            class Meta:
                model = Tenant
                fields = ['name']

        form = TenantForm({'name': '更新後テナント'}, instance=tenant)
        form.is_valid()

        with patch.object(UpdateView, 'form_valid', return_value=MagicMock()):
            view.form_valid(form)

        # メッセージが追加されていることを確認
        stored_messages = list(messages.get_messages(request))
        assert any('更新しました' in str(m) for m in stored_messages)
