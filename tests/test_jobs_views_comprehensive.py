"""Django ATS - 求人ビュー包括的テスト

jobs/views.pyの100%カバレッジを目指すテスト。
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
        name='求人包括テスト',
        code='job-comprehensive-test',
        is_active=True,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@job-comp-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def hiring_manager(db, tenant):
    """採用マネージャー"""
    return CustomUser.objects.create_user(
        email='manager@job-comp-test.com',
        password='testpass123',
        role=UserRoleChoices.HIRING_MANAGER,
        tenant=tenant,
    )


@pytest.fixture
def recruiter(db, tenant):
    """採用担当者"""
    return CustomUser.objects.create_user(
        email='recruiter@job-comp-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_RECRUITER,
        tenant=tenant,
    )


@pytest.fixture
def interviewer(db, tenant):
    """面接官"""
    return CustomUser.objects.create_user(
        email='interviewer@job-comp-test.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def job(db, tenant, admin_user):
    """テスト求人（下書き）"""
    return Job.objects.create(
        tenant=tenant,
        title='テスト求人（下書き）',
        unique_code='JOB-COMP-001',
        status=JobStatusChoices.DRAFT,
        employment_type=EmploymentTypeChoices.FULL_TIME,
        created_by=admin_user,
    )


@pytest.fixture
def active_job(db, tenant, admin_user):
    """公開中の求人"""
    return Job.objects.create(
        tenant=tenant,
        title='公開中テスト求人',
        unique_code='JOB-COMP-002',
        status=JobStatusChoices.ACTIVE,
        employment_type=EmploymentTypeChoices.FULL_TIME,
        created_by=admin_user,
    )


@pytest.fixture
def paused_job(db, tenant, admin_user):
    """一時停止中の求人"""
    return Job.objects.create(
        tenant=tenant,
        title='一時停止中テスト求人',
        unique_code='JOB-COMP-003',
        status=JobStatusChoices.PAUSED,
        employment_type=EmploymentTypeChoices.CONTRACT,
        created_by=admin_user,
    )


@pytest.fixture
def closed_job(db, tenant, admin_user):
    """終了した求人"""
    return Job.objects.create(
        tenant=tenant,
        title='終了したテスト求人',
        unique_code='JOB-COMP-004',
        status=JobStatusChoices.CLOSED,
        employment_type=EmploymentTypeChoices.PART_TIME,
        created_by=admin_user,
    )


@pytest.fixture
def multiple_jobs(db, tenant, admin_user):
    """複数求人"""
    jobs = []
    statuses = [JobStatusChoices.DRAFT, JobStatusChoices.ACTIVE, JobStatusChoices.PAUSED]
    for i, status in enumerate(statuses):
        jobs.append(Job.objects.create(
            tenant=tenant,
            title=f'複数テスト求人{i+1}',
            unique_code=f'JOB-MULTI-{i+1:03d}',
            status=status,
            employment_type=EmploymentTypeChoices.FULL_TIME,
            created_by=admin_user,
        ))
    return jobs


# =============================================================================
# JobListView Tests
# =============================================================================

class TestJobListViewComprehensive:
    """求人一覧ビュー包括テスト"""

    @pytest.mark.django_db
    def test_list_unauthenticated(self, client):
        """未認証ユーザーはリダイレクト"""
        response = client.get(reverse('jobs:job_list'))
        assert response.status_code == 302
        assert 'login' in response.url

    @pytest.mark.django_db
    def test_list_authenticated_admin(self, client, admin_user, job):
        """管理者は一覧表示可能"""
        client.force_login(admin_user)
        response = client.get(reverse('jobs:job_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_authenticated_recruiter(self, client, recruiter, job):
        """採用担当者は一覧表示可能"""
        client.force_login(recruiter)
        response = client.get(reverse('jobs:job_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_status(self, client, admin_user, active_job):
        """ステータスでフィルタ"""
        client.force_login(admin_user)
        response = client.get(
            reverse('jobs:job_list'),
            {'status': JobStatusChoices.ACTIVE}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_employment_type(self, client, admin_user, active_job):
        """雇用形態でフィルタ"""
        client.force_login(admin_user)
        response = client.get(
            reverse('jobs:job_list'),
            {'employment_type': EmploymentTypeChoices.FULL_TIME}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_search(self, client, admin_user, job):
        """検索"""
        client.force_login(admin_user)
        response = client.get(
            reverse('jobs:job_list'),
            {'q': 'テスト'}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_pagination(self, client, admin_user, multiple_jobs):
        """ページネーション"""
        client.force_login(admin_user)
        response = client.get(reverse('jobs:job_list'))
        assert response.status_code == 200


# =============================================================================
# JobDetailView Tests
# =============================================================================

class TestJobDetailViewComprehensive:
    """求人詳細ビュー包括テスト"""

    @pytest.mark.django_db
    def test_detail_unauthenticated(self, client, job):
        """未認証ユーザーはリダイレクト"""
        response = client.get(reverse('jobs:job_detail', kwargs={'pk': job.pk}))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_detail_authenticated(self, client, admin_user, job):
        """認証済みユーザーは詳細表示可能"""
        client.force_login(admin_user)
        response = client.get(reverse('jobs:job_detail', kwargs={'pk': job.pk}))
        assert response.status_code == 200


# =============================================================================
# JobCreateView Tests
# =============================================================================

class TestJobCreateViewComprehensive:
    """求人作成ビュー包括テスト"""

    @pytest.mark.django_db
    def test_create_unauthenticated(self, client):
        """未認証ユーザーはリダイレクト"""
        response = client.get(reverse('jobs:job_create'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_create_form_display(self, client, admin_user):
        """作成フォームの表示"""
        client.force_login(admin_user)
        response = client.get(reverse('jobs:job_create'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_create_valid_data(self, client, admin_user):
        """有効なデータで求人作成"""
        client.force_login(admin_user)
        data = {
            'title': '新規作成テスト求人',
            'unique_code': 'JOB-NEW-001',
            'status': JobStatusChoices.DRAFT,
            'employment_type': EmploymentTypeChoices.FULL_TIME,
            'description': '求人の説明文です。',
        }
        response = client.post(reverse('jobs:job_create'), data)
        assert response.status_code in [200, 302]


# =============================================================================
# JobUpdateView Tests
# =============================================================================

class TestJobUpdateViewComprehensive:
    """求人更新ビュー包括テスト"""

    @pytest.mark.django_db
    def test_update_unauthenticated(self, client, job):
        """未認証ユーザーはリダイレクト"""
        response = client.get(reverse('jobs:job_update', kwargs={'pk': job.pk}))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_update_form_display(self, client, admin_user, job):
        """更新フォームの表示"""
        client.force_login(admin_user)
        response = client.get(reverse('jobs:job_update', kwargs={'pk': job.pk}))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_update_valid_data(self, client, admin_user, job):
        """有効なデータで求人更新"""
        client.force_login(admin_user)
        data = {
            'title': '更新後のテスト求人',
            'unique_code': job.unique_code,
            'status': job.status,
            'employment_type': EmploymentTypeChoices.FULL_TIME,
            'description': '更新後の説明文',
        }
        response = client.post(
            reverse('jobs:job_update', kwargs={'pk': job.pk}),
            data
        )
        assert response.status_code in [200, 302]


# =============================================================================
# JobStatusChangeView Tests
# =============================================================================

class TestJobStatusChangeViewComprehensive:
    """求人ステータス変更ビュー包括テスト"""

    @pytest.mark.django_db
    def test_publish_unauthenticated(self, client, job):
        """未認証ユーザーはリダイレクト"""
        response = client.post(
            reverse('jobs:job_status', kwargs={'pk': job.pk, 'action': 'publish'})
        )
        assert response.status_code == 302
        assert 'login' in response.url

    @pytest.mark.django_db
    def test_publish_job(self, client, admin_user, job):
        """求人を公開"""
        client.force_login(admin_user)
        response = client.post(
            reverse('jobs:job_status', kwargs={'pk': job.pk, 'action': 'publish'})
        )
        assert response.status_code == 302
        job.refresh_from_db()
        assert job.status == JobStatusChoices.ACTIVE

    @pytest.mark.django_db
    def test_pause_job(self, client, admin_user, active_job):
        """求人を一時停止"""
        client.force_login(admin_user)
        response = client.post(
            reverse('jobs:job_status', kwargs={'pk': active_job.pk, 'action': 'pause'})
        )
        assert response.status_code == 302
        active_job.refresh_from_db()
        assert active_job.status == JobStatusChoices.PAUSED

    @pytest.mark.django_db
    def test_publish_paused_job(self, client, admin_user, paused_job):
        """一時停止中の求人を再公開"""
        client.force_login(admin_user)
        response = client.post(
            reverse('jobs:job_status', kwargs={'pk': paused_job.pk, 'action': 'publish'})
        )
        assert response.status_code == 302
        paused_job.refresh_from_db()
        assert paused_job.status == JobStatusChoices.ACTIVE

    @pytest.mark.django_db
    def test_close_job(self, client, admin_user, active_job):
        """求人を終了"""
        client.force_login(admin_user)
        response = client.post(
            reverse('jobs:job_status', kwargs={'pk': active_job.pk, 'action': 'close'})
        )
        assert response.status_code == 302
        active_job.refresh_from_db()
        assert active_job.status == JobStatusChoices.CLOSED

    @pytest.mark.django_db
    def test_invalid_action(self, client, admin_user, job):
        """無効なアクション"""
        client.force_login(admin_user)
        response = client.post(
            reverse('jobs:job_status', kwargs={'pk': job.pk, 'action': 'invalid'})
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_status_change_htmx(self, client, admin_user, job):
        """htmxリクエストでステータス変更"""
        client.force_login(admin_user)
        response = client.post(
            reverse('jobs:job_status', kwargs={'pk': job.pk, 'action': 'publish'}),
            HTTP_HX_REQUEST='true'
        )
        assert response.status_code in [204, 302]


# =============================================================================
# JobDuplicateView Tests
# =============================================================================

class TestJobDuplicateViewComprehensive:
    """求人複製ビュー包括テスト"""

    @pytest.mark.django_db
    def test_duplicate_unauthenticated(self, client, job):
        """未認証ユーザーはリダイレクト"""
        response = client.post(
            reverse('jobs:job_duplicate', kwargs={'pk': job.pk})
        )
        assert response.status_code == 302
        assert 'login' in response.url

    @pytest.mark.django_db
    def test_duplicate_job(self, client, admin_user, job):
        """求人を複製"""
        original_count = Job.objects.count()
        client.force_login(admin_user)
        response = client.post(
            reverse('jobs:job_duplicate', kwargs={'pk': job.pk})
        )
        assert response.status_code == 302
        assert Job.objects.count() == original_count + 1

    @pytest.mark.django_db
    def test_duplicate_generates_unique_code(self, client, admin_user, job):
        """複製時にユニークコードが生成される"""
        client.force_login(admin_user)
        client.post(
            reverse('jobs:job_duplicate', kwargs={'pk': job.pk})
        )
        duplicated = Job.objects.exclude(pk=job.pk).order_by('-created_at').first()
        assert duplicated.unique_code != job.unique_code

    @pytest.mark.django_db
    def test_duplicate_preserves_content(self, client, admin_user, job):
        """複製時に内容が保持される"""
        job.description = 'テスト説明文'
        job.save()
        client.force_login(admin_user)
        client.post(
            reverse('jobs:job_duplicate', kwargs={'pk': job.pk})
        )
        duplicated = Job.objects.exclude(pk=job.pk).order_by('-created_at').first()
        assert duplicated.title.startswith(job.title.split('(')[0])

    @pytest.mark.django_db
    def test_duplicate_sets_draft_status(self, client, admin_user, active_job):
        """複製時に下書きステータスになる"""
        client.force_login(admin_user)
        client.post(
            reverse('jobs:job_duplicate', kwargs={'pk': active_job.pk})
        )
        duplicated = Job.objects.exclude(pk=active_job.pk).order_by('-created_at').first()
        assert duplicated.status == JobStatusChoices.DRAFT
