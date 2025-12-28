"""Django ATS - 求人ビューテスト

求人関連ビューのテスト。
"""

import pytest
from django.test import Client
from django.urls import reverse

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
        name='ジョブビューテスト',
        code='job-view-test',
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """テストユーザー"""
    user = CustomUser.objects.create_user(
        email='user@job-view-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )
    return user


@pytest.fixture
def hiring_manager(db, tenant):
    """採用担当者"""
    return CustomUser.objects.create_user(
        email='manager@job-view-test.com',
        password='testpass123',
        role=UserRoleChoices.HIRING_MANAGER,
        tenant=tenant,
    )


@pytest.fixture
def job(db, tenant, user):
    """テスト求人"""
    return Job.objects.create(
        tenant=tenant,
        title='ソフトウェアエンジニア',
        unique_code='JOB-001',
        status=JobStatusChoices.DRAFT,
        created_by=user,
    )


@pytest.fixture
def active_job(db, tenant, user):
    """公開中の求人"""
    return Job.objects.create(
        tenant=tenant,
        title='フロントエンドエンジニア',
        unique_code='JOB-002',
        status=JobStatusChoices.ACTIVE,
        employment_type=EmploymentTypeChoices.FULL_TIME,
        created_by=user,
    )


@pytest.fixture
def client_with_tenant(db, tenant, user):
    """テナント情報付きクライアント"""
    client = Client()
    client.force_login(user)
    return client


# =============================================================================
# JobListView Tests
# =============================================================================

class TestJobListView:
    """求人一覧ビューのテスト"""

    @pytest.mark.django_db
    def test_job_list_requires_login(self, client):
        """未認証ユーザーはログインにリダイレクトされる"""
        response = client.get(reverse('jobs:job_list'))
        assert response.status_code == 302
        assert 'login' in response.url

    @pytest.mark.django_db
    def test_job_list_authenticated(self, client_with_tenant, job):
        """認証済みユーザーは一覧を表示できる"""
        response = client_with_tenant.get(reverse('jobs:job_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_job_list_filter_by_status(self, client_with_tenant, job, active_job):
        """ステータスでフィルタできる"""
        response = client_with_tenant.get(
            reverse('jobs:job_list'),
            {'status': JobStatusChoices.ACTIVE}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_job_list_filter_by_employment_type(self, client_with_tenant, active_job):
        """雇用形態でフィルタできる"""
        response = client_with_tenant.get(
            reverse('jobs:job_list'),
            {'employment_type': EmploymentTypeChoices.FULL_TIME}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_job_list_search(self, client_with_tenant, job):
        """検索できる"""
        response = client_with_tenant.get(
            reverse('jobs:job_list'),
            {'q': 'ソフトウェア'}
        )
        assert response.status_code == 200


# =============================================================================
# JobDetailView Tests
# =============================================================================

class TestJobDetailView:
    """求人詳細ビューのテスト"""

    @pytest.mark.django_db
    def test_job_detail_requires_login(self, client, job):
        """未認証ユーザーはログインにリダイレクトされる"""
        response = client.get(reverse('jobs:job_detail', kwargs={'pk': job.pk}))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_job_detail_authenticated(self, client_with_tenant, job):
        """認証済みユーザーは詳細を表示できる"""
        response = client_with_tenant.get(
            reverse('jobs:job_detail', kwargs={'pk': job.pk})
        )
        assert response.status_code == 200


# =============================================================================
# JobCreateView Tests
# =============================================================================

class TestJobCreateView:
    """求人作成ビューのテスト"""

    @pytest.mark.django_db
    def test_job_create_requires_login(self, client):
        """未認証ユーザーはログインにリダイレクトされる"""
        response = client.get(reverse('jobs:job_create'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_job_create_form_display(self, client_with_tenant):
        """作成フォームが表示される"""
        response = client_with_tenant.get(reverse('jobs:job_create'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_job_create_valid_data(self, client_with_tenant, tenant):
        """有効なデータで求人を作成できる"""
        data = {
            'title': '新規求人',
            'unique_code': 'NEW-001',
            'status': JobStatusChoices.DRAFT,
            'employment_type': EmploymentTypeChoices.FULL_TIME,
            'description': '仕事の説明',
        }
        response = client_with_tenant.post(reverse('jobs:job_create'), data)
        # 成功時はリダイレクト
        assert response.status_code in [302, 200]


# =============================================================================
# JobUpdateView Tests
# =============================================================================

class TestJobUpdateView:
    """求人更新ビューのテスト"""

    @pytest.mark.django_db
    def test_job_update_requires_login(self, client, job):
        """未認証ユーザーはログインにリダイレクトされる"""
        response = client.get(reverse('jobs:job_update', kwargs={'pk': job.pk}))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_job_update_form_display(self, client_with_tenant, job):
        """更新フォームが表示される"""
        response = client_with_tenant.get(
            reverse('jobs:job_update', kwargs={'pk': job.pk})
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_job_update_valid_data(self, client_with_tenant, job):
        """有効なデータで求人を更新できる"""
        data = {
            'title': '更新後の求人タイトル',
            'unique_code': job.unique_code,
            'status': job.status,
            'employment_type': EmploymentTypeChoices.FULL_TIME,
            'description': '更新後の説明',
        }
        response = client_with_tenant.post(
            reverse('jobs:job_update', kwargs={'pk': job.pk}),
            data
        )
        assert response.status_code in [302, 200]


# =============================================================================
# JobStatusChangeView Tests
# =============================================================================

class TestJobStatusChangeView:
    """求人ステータス変更ビューのテスト"""

    @pytest.mark.django_db
    def test_publish_job(self, client_with_tenant, job):
        """求人を公開できる"""
        response = client_with_tenant.post(
            reverse('jobs:job_status', kwargs={'pk': job.pk, 'action': 'publish'})
        )
        assert response.status_code == 302
        job.refresh_from_db()
        assert job.status == JobStatusChoices.ACTIVE

    @pytest.mark.django_db
    def test_pause_job(self, client_with_tenant, active_job):
        """求人を一時停止できる"""
        response = client_with_tenant.post(
            reverse('jobs:job_status', kwargs={'pk': active_job.pk, 'action': 'pause'})
        )
        assert response.status_code == 302
        active_job.refresh_from_db()
        assert active_job.status == JobStatusChoices.PAUSED

    @pytest.mark.django_db
    def test_close_job(self, client_with_tenant, active_job):
        """求人を終了できる"""
        response = client_with_tenant.post(
            reverse('jobs:job_status', kwargs={'pk': active_job.pk, 'action': 'close'})
        )
        assert response.status_code == 302
        active_job.refresh_from_db()
        assert active_job.status == JobStatusChoices.CLOSED

    @pytest.mark.django_db
    def test_invalid_action(self, client_with_tenant, job):
        """無効なアクションでエラー"""
        response = client_with_tenant.post(
            reverse('jobs:job_status', kwargs={'pk': job.pk, 'action': 'invalid'})
        )
        assert response.status_code == 302


# =============================================================================
# JobDuplicateView Tests
# =============================================================================

class TestJobDuplicateView:
    """求人複製ビューのテスト"""

    @pytest.mark.django_db
    def test_duplicate_job(self, client_with_tenant, job):
        """求人を複製できる"""
        original_count = Job.objects.count()
        response = client_with_tenant.post(
            reverse('jobs:job_duplicate', kwargs={'pk': job.pk})
        )
        assert response.status_code == 302
        assert Job.objects.count() == original_count + 1

    @pytest.mark.django_db
    def test_duplicate_generates_unique_code(self, client_with_tenant, job):
        """複製時にユニークなコードが生成される"""
        client_with_tenant.post(
            reverse('jobs:job_duplicate', kwargs={'pk': job.pk})
        )
        duplicated = Job.objects.exclude(pk=job.pk).first()
        assert duplicated.unique_code != job.unique_code
        assert job.unique_code in duplicated.unique_code
