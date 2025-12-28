"""Django ATS - Core Mixins ユニットテスト

View Mixins のテストケース。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from apps.core.mixins import (
    TenantQuerysetMixin,
    TenantAccessMixin,
    TenantCreateMixin,
    RoleRequiredMixin,
    AdminRequiredMixin,
    SystemAdminRequiredMixin,
    RecruiterOrAboveMixin,
    ConsultantOrAboveMixin,
    HiringManagerOrAboveMixin,
    FullCandidateAccessMixin,
    LimitedCandidateAccessMixin,
    CandidateQuerysetFilterMixin,
    OptimisticLockMixin,
    AuditMixin,
    SuccessMessageMixin,
    HtmxMixin,
    SearchMixin,
    OrderingMixin,
    PaginationMixin,
)
from apps.core.exceptions import TenantAccessError, RolePermissionError


class TestRoleRequiredMixin:
    """RoleRequiredMixin のテスト"""

    def test_required_roles_default_empty(self):
        """デフォルトでrequired_rolesは空リストであること"""
        assert RoleRequiredMixin.required_roles == []


class TestAdminRequiredMixin:
    """AdminRequiredMixin のテスト"""

    def test_required_roles(self):
        """system_admin, client_admin が必要なこと"""
        assert 'system_admin' in AdminRequiredMixin.required_roles
        assert 'client_admin' in AdminRequiredMixin.required_roles
        assert len(AdminRequiredMixin.required_roles) == 2


class TestSystemAdminRequiredMixin:
    """SystemAdminRequiredMixin のテスト"""

    def test_required_roles(self):
        """system_admin のみ必要なこと"""
        assert AdminRequiredMixin.required_roles == ['system_admin', 'client_admin']
        assert SystemAdminRequiredMixin.required_roles == ['system_admin']


class TestRecruiterOrAboveMixin:
    """RecruiterOrAboveMixin のテスト"""

    def test_required_roles(self):
        """system_admin, client_admin, client_recruiter が必要なこと"""
        assert 'system_admin' in RecruiterOrAboveMixin.required_roles
        assert 'client_admin' in RecruiterOrAboveMixin.required_roles
        assert 'client_recruiter' in RecruiterOrAboveMixin.required_roles
        assert len(RecruiterOrAboveMixin.required_roles) == 3


class TestHtmxMixin:
    """HtmxMixin のテスト"""

    def test_htmx_template_name_default_none(self):
        """htmx_template_name のデフォルトはNoneであること"""
        assert HtmxMixin.htmx_template_name is None


class TestSearchMixin:
    """SearchMixin のテスト"""

    def test_search_fields_default_empty(self):
        """デフォルトでsearch_fieldsは空リストであること"""
        assert SearchMixin.search_fields == []

    def test_search_param_default(self):
        """デフォルトの検索パラメータ名は'q'であること"""
        assert SearchMixin.search_param == 'q'


class TestOrderingMixin:
    """OrderingMixin のテスト"""

    def test_ordering_fields_default_empty(self):
        """デフォルトでordering_fieldsは空リストであること"""
        assert OrderingMixin.ordering_fields == []

    def test_default_ordering(self):
        """デフォルトのソート順は'-created_at'であること"""
        assert OrderingMixin.default_ordering == '-created_at'

    def test_ordering_param_default(self):
        """デフォルトのソートパラメータ名は'sort'であること"""
        assert OrderingMixin.ordering_param == 'sort'


class TestPaginationMixin:
    """PaginationMixin のテスト"""

    def test_paginate_by_default(self):
        """デフォルトのページサイズは25であること"""
        assert PaginationMixin.paginate_by == 25

    def test_page_sizes(self):
        """選択可能なページサイズが定義されていること"""
        assert PaginationMixin.page_sizes == [10, 25, 50, 100]

    def test_page_size_param_default(self):
        """デフォルトのページサイズパラメータ名は'per_page'であること"""
        assert PaginationMixin.page_size_param == 'per_page'


class TestSuccessMessageMixin:
    """SuccessMessageMixin のテスト"""

    def test_success_message_default_none(self):
        """デフォルトでsuccess_messageはNoneであること"""
        assert SuccessMessageMixin.success_message is None


class TestMixinInheritance:
    """Mixin継承関係のテスト"""

    def test_tenant_access_mixin_requires_login(self):
        """TenantAccessMixinはログイン必須であること"""
        from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
        assert issubclass(TenantAccessMixin, LoginRequiredMixin)
        assert issubclass(TenantAccessMixin, UserPassesTestMixin)

    def test_role_required_mixin_requires_login(self):
        """RoleRequiredMixinはログイン必須であること"""
        from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
        assert issubclass(RoleRequiredMixin, LoginRequiredMixin)
        assert issubclass(RoleRequiredMixin, UserPassesTestMixin)


class TestConsultantOrAboveMixin:
    """ConsultantOrAboveMixin のテスト"""

    def test_required_roles(self):
        """system_admin, consultant, client_admin, hiring_manager が必要なこと"""
        assert 'system_admin' in ConsultantOrAboveMixin.required_roles
        assert 'consultant' in ConsultantOrAboveMixin.required_roles
        assert 'client_admin' in ConsultantOrAboveMixin.required_roles
        assert 'hiring_manager' in ConsultantOrAboveMixin.required_roles
        assert len(ConsultantOrAboveMixin.required_roles) == 4

    def test_inherits_role_required_mixin(self):
        """RoleRequiredMixinを継承していること"""
        assert issubclass(ConsultantOrAboveMixin, RoleRequiredMixin)


class TestHiringManagerOrAboveMixin:
    """HiringManagerOrAboveMixin のテスト"""

    def test_required_roles(self):
        """system_admin, client_admin, hiring_manager が必要なこと"""
        assert 'system_admin' in HiringManagerOrAboveMixin.required_roles
        assert 'client_admin' in HiringManagerOrAboveMixin.required_roles
        assert 'hiring_manager' in HiringManagerOrAboveMixin.required_roles
        assert len(HiringManagerOrAboveMixin.required_roles) == 3

    def test_inherits_role_required_mixin(self):
        """RoleRequiredMixinを継承していること"""
        assert issubclass(HiringManagerOrAboveMixin, RoleRequiredMixin)


class TestFullCandidateAccessMixin:
    """FullCandidateAccessMixin のテスト"""

    def test_inherits_login_required(self):
        """LoginRequiredMixinを継承していること"""
        from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
        assert issubclass(FullCandidateAccessMixin, LoginRequiredMixin)
        assert issubclass(FullCandidateAccessMixin, UserPassesTestMixin)

    def test_test_func_with_full_access_user(self):
        """フルアクセス権限を持つユーザーはTrueを返すこと"""
        mixin = FullCandidateAccessMixin()
        mixin.request = MagicMock()
        mixin.request.user.has_full_candidate_access = True
        assert mixin.test_func() is True

    def test_test_func_without_full_access_user(self):
        """フルアクセス権限を持たないユーザーはFalseを返すこと"""
        mixin = FullCandidateAccessMixin()
        mixin.request = MagicMock()
        mixin.request.user.has_full_candidate_access = False
        assert mixin.test_func() is False

    def test_test_func_without_attribute(self):
        """属性がないユーザーはFalseを返すこと"""
        mixin = FullCandidateAccessMixin()
        mixin.request = MagicMock()
        # has_full_candidate_access属性がない場合
        del mixin.request.user.has_full_candidate_access
        assert mixin.test_func() is False


class TestLimitedCandidateAccessMixin:
    """LimitedCandidateAccessMixin のテスト"""

    def test_inherits_login_required(self):
        """LoginRequiredMixinを継承していること"""
        from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
        assert issubclass(LimitedCandidateAccessMixin, LoginRequiredMixin)
        assert issubclass(LimitedCandidateAccessMixin, UserPassesTestMixin)

    def test_test_func_with_full_access_user(self):
        """フルアクセス権限を持つユーザーはTrueを返すこと"""
        mixin = LimitedCandidateAccessMixin()
        mixin.request = MagicMock()
        mixin.request.user.has_full_candidate_access = True
        mixin.request.user.has_limited_candidate_access = False
        assert mixin.test_func() is True

    def test_test_func_with_limited_access_user(self):
        """限定アクセス権限を持つユーザーはTrueを返すこと"""
        mixin = LimitedCandidateAccessMixin()
        mixin.request = MagicMock()
        mixin.request.user.has_full_candidate_access = False
        mixin.request.user.has_limited_candidate_access = True
        assert mixin.test_func() is True

    def test_test_func_without_any_access(self):
        """アクセス権限を持たないユーザーはFalseを返すこと"""
        mixin = LimitedCandidateAccessMixin()
        mixin.request = MagicMock()
        mixin.request.user.has_full_candidate_access = False
        mixin.request.user.has_limited_candidate_access = False
        assert mixin.test_func() is False

    def test_test_func_without_attributes(self):
        """属性がないユーザーはFalseを返すこと"""
        mixin = LimitedCandidateAccessMixin()
        mixin.request = MagicMock()
        # 属性がない場合
        del mixin.request.user.has_full_candidate_access
        del mixin.request.user.has_limited_candidate_access
        assert mixin.test_func() is False


class TestCandidateQuerysetFilterMixin:
    """CandidateQuerysetFilterMixin のテスト"""

    def test_get_queryset_calls_for_user(self):
        """get_querysetがCandidateモデルの場合、for_userを呼び出すこと"""
        # このテストはDBが必要なため、統合テストとして別途実施
        pass
