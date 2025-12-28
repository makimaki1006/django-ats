"""Django ATS - 求人フォームテスト

JobForm, JobFilterForm のテスト。
"""

import pytest
from django.core.exceptions import ValidationError

from apps.jobs.forms import JobForm, JobFilterForm
from apps.jobs.models import Job, JobStatusChoices, EmploymentTypeChoices
from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='求人フォームテスト',
        code='job-form-test',
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """テストユーザー"""
    return CustomUser.objects.create_user(
        email='user@job-form-test.com',
        password='testpass123',
        tenant=tenant,
        role=UserRoleChoices.CLIENT_ADMIN,
    )


@pytest.fixture
def hiring_manager(db, tenant):
    """採用責任者"""
    return CustomUser.objects.create_user(
        email='manager@job-form-test.com',
        password='testpass123',
        tenant=tenant,
        role=UserRoleChoices.HIRING_MANAGER,
    )


@pytest.fixture
def existing_job(db, tenant, user):
    """既存の求人"""
    return Job.objects.create(
        tenant=tenant,
        title='既存求人',
        unique_code='EXISTING-001',
        status=JobStatusChoices.ACTIVE,
        created_by=user,
    )


# =============================================================================
# JobForm Tests
# =============================================================================

class TestJobForm:
    """JobForm のテスト"""

    @pytest.mark.django_db
    def test_form_valid_data(self, tenant, hiring_manager):
        """有効なデータでフォームが通る"""
        form = JobForm(
            data={
                'title': 'ソフトウェアエンジニア',
                'unique_code': 'JOB-2025-001',
                'status': JobStatusChoices.DRAFT,
                'employment_type': EmploymentTypeChoices.FULL_TIME,
                'hiring_manager': hiring_manager.pk,
                'headcount': 1,
            },
            tenant=tenant,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_form_without_tenant(self):
        """テナントなしでもフォームは作成可能"""
        form = JobForm(
            data={
                'title': 'テスト求人',
                'unique_code': 'TEST-001',
                'status': JobStatusChoices.DRAFT,
                'employment_type': EmploymentTypeChoices.FULL_TIME,
                'headcount': 1,
            },
            tenant=None,
        )
        # unique_codeの重複チェックはテナントがないとスキップ
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_form_filters_hiring_manager_by_tenant(self, tenant, hiring_manager):
        """採用責任者はテナントでフィルタリングされる"""
        # 別テナントのユーザー
        other_tenant = Tenant.objects.create(
            name='別テナント',
            code='other-tenant',
        )
        other_user = CustomUser.objects.create_user(
            email='other@other-tenant.com',
            password='testpass123',
            tenant=other_tenant,
            role=UserRoleChoices.HIRING_MANAGER,
        )

        form = JobForm(tenant=tenant)
        queryset = form.fields['hiring_manager'].queryset

        assert hiring_manager in queryset
        assert other_user not in queryset

    @pytest.mark.django_db
    def test_unique_code_duplicate_validation(self, tenant, existing_job, hiring_manager):
        """同一テナント内での求人コード重複をエラーにする"""
        form = JobForm(
            data={
                'title': '新規求人',
                'unique_code': 'EXISTING-001',  # 既存と同じコード
                'status': JobStatusChoices.DRAFT,
                'employment_type': EmploymentTypeChoices.FULL_TIME,
                'hiring_manager': hiring_manager.pk,
            },
            tenant=tenant,
        )
        assert not form.is_valid()
        assert 'unique_code' in form.errors
        assert '既に使用されています' in str(form.errors['unique_code'])

    @pytest.mark.django_db
    def test_unique_code_same_on_update(self, tenant, existing_job, hiring_manager):
        """更新時は自分自身の求人コードはOK"""
        form = JobForm(
            data={
                'title': '更新後求人',
                'unique_code': 'EXISTING-001',  # 同じコード
                'status': JobStatusChoices.ACTIVE,
                'employment_type': EmploymentTypeChoices.FULL_TIME,
                'hiring_manager': hiring_manager.pk,
                'headcount': 1,
            },
            instance=existing_job,
            tenant=tenant,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_salary_range_validation(self, tenant, hiring_manager):
        """年収範囲の整合性チェック"""
        form = JobForm(
            data={
                'title': '年収テスト',
                'unique_code': 'SALARY-001',
                'status': JobStatusChoices.DRAFT,
                'employment_type': EmploymentTypeChoices.FULL_TIME,
                'hiring_manager': hiring_manager.pk,
                'salary_min': 800,  # 下限が上限より大きい
                'salary_max': 500,
            },
            tenant=tenant,
        )
        assert not form.is_valid()
        assert 'salary_max' in form.errors
        assert '下限以上' in str(form.errors['salary_max'])

    @pytest.mark.django_db
    def test_salary_range_valid(self, tenant, hiring_manager):
        """有効な年収範囲"""
        form = JobForm(
            data={
                'title': '年収テスト',
                'unique_code': 'SALARY-002',
                'status': JobStatusChoices.DRAFT,
                'employment_type': EmploymentTypeChoices.FULL_TIME,
                'hiring_manager': hiring_manager.pk,
                'salary_min': 500,
                'salary_max': 800,
                'headcount': 1,
            },
            tenant=tenant,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_salary_only_min(self, tenant, hiring_manager):
        """年収下限のみ設定可能"""
        form = JobForm(
            data={
                'title': '年収テスト',
                'unique_code': 'SALARY-003',
                'status': JobStatusChoices.DRAFT,
                'employment_type': EmploymentTypeChoices.FULL_TIME,
                'hiring_manager': hiring_manager.pk,
                'salary_min': 500,
                'headcount': 1,
            },
            tenant=tenant,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_salary_only_max(self, tenant, hiring_manager):
        """年収上限のみ設定可能"""
        form = JobForm(
            data={
                'title': '年収テスト',
                'unique_code': 'SALARY-004',
                'status': JobStatusChoices.DRAFT,
                'employment_type': EmploymentTypeChoices.FULL_TIME,
                'hiring_manager': hiring_manager.pk,
                'salary_max': 800,
                'headcount': 1,
            },
            tenant=tenant,
        )
        assert form.is_valid(), form.errors


# =============================================================================
# JobFilterForm Tests
# =============================================================================

class TestJobFilterForm:
    """JobFilterForm のテスト"""

    @pytest.mark.django_db
    def test_filter_form_empty(self):
        """空のフィルタフォームは有効"""
        form = JobFilterForm(data={})
        assert form.is_valid()

    @pytest.mark.django_db
    def test_filter_form_with_query(self):
        """検索クエリ付きフォーム"""
        form = JobFilterForm(data={'q': 'エンジニア'})
        assert form.is_valid()
        assert form.cleaned_data['q'] == 'エンジニア'

    @pytest.mark.django_db
    def test_filter_form_with_status(self):
        """ステータスフィルタ"""
        form = JobFilterForm(data={'status': JobStatusChoices.ACTIVE})
        assert form.is_valid()
        assert form.cleaned_data['status'] == JobStatusChoices.ACTIVE

    @pytest.mark.django_db
    def test_filter_form_with_employment_type(self):
        """雇用形態フィルタ"""
        form = JobFilterForm(data={'employment_type': EmploymentTypeChoices.FULL_TIME})
        assert form.is_valid()
        assert form.cleaned_data['employment_type'] == EmploymentTypeChoices.FULL_TIME

    @pytest.mark.django_db
    def test_filter_form_all_filters(self):
        """全フィルタ組み合わせ"""
        form = JobFilterForm(data={
            'q': 'バックエンド',
            'status': JobStatusChoices.ACTIVE,
            'employment_type': EmploymentTypeChoices.FULL_TIME,
        })
        assert form.is_valid()
        assert form.cleaned_data['q'] == 'バックエンド'
        assert form.cleaned_data['status'] == JobStatusChoices.ACTIVE
        assert form.cleaned_data['employment_type'] == EmploymentTypeChoices.FULL_TIME

    @pytest.mark.django_db
    def test_filter_form_all_status_option(self):
        """すべてのステータスオプション"""
        form = JobFilterForm(data={'status': ''})
        assert form.is_valid()
        assert form.cleaned_data['status'] == ''

    @pytest.mark.django_db
    def test_filter_form_all_employment_type_option(self):
        """すべての雇用形態オプション"""
        form = JobFilterForm(data={'employment_type': ''})
        assert form.is_valid()
        assert form.cleaned_data['employment_type'] == ''
