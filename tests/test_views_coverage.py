"""Django ATS - ビューカバレッジ向上テスト

各ビューのform_valid、get_success_url等の未カバーメソッドをテスト。
"""

import pytest
from django.urls import reverse
from django.contrib.messages import get_messages

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRole
from apps.candidates.models import Candidate
from apps.jobs.models import Job, JobStatusChoices
from apps.applications.models import Application, ApplicationStatusChoices
from apps.interviews.models import Interview, InterviewStatusChoices


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='ビューテスト',
        code='view-coverage-test',
        is_active=True,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@view-coverage-test.com',
        password='testpass123',
        role=UserRole.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def candidate(db, tenant, admin_user):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        email='candidate@view-coverage-test.com',
        name='テスト候補者',
        registered_by=admin_user,
    )


@pytest.fixture
def active_job(db, tenant, admin_user):
    """アクティブな求人"""
    return Job.objects.create(
        tenant=tenant,
        title='テスト求人',
        unique_code='JOB-VIEW-001',
        status=JobStatusChoices.ACTIVE,
        created_by=admin_user,
    )


@pytest.fixture
def application(db, tenant, candidate, active_job):
    """テスト応募"""
    return Application.objects.create(
        tenant=tenant,
        candidate=candidate,
        job=active_job,
        status=ApplicationStatusChoices.NEW,
    )


@pytest.fixture
def interview(db, tenant, active_job, application, admin_user):
    """テスト面接"""
    from datetime import timedelta
    from django.utils import timezone

    return Interview.objects.create(
        tenant=tenant,
        application=application,
        interviewer=admin_user,
        scheduled_at=timezone.now() + timedelta(days=7),
        status=InterviewStatusChoices.SCHEDULED,
        interview_type='video',  # InterviewTypeChoices.VIDEO
        duration_minutes=60,
    )


@pytest.fixture
def authenticated_client(client, admin_user, tenant):
    """認証済みクライアント"""
    client.force_login(admin_user)
    # テナントセッションを設定
    session = client.session
    session['tenant_id'] = str(tenant.pk)
    session.save()
    return client


# =============================================================================
# Job View Tests
# =============================================================================

class TestJobCreateView:
    """求人作成ビューテスト"""

    @pytest.mark.django_db
    def test_form_valid_creates_job(self, authenticated_client, tenant, admin_user):
        """フォーム送信で求人が作成される"""
        url = reverse('jobs:job_create')
        data = {
            'title': '新規求人',
            'unique_code': 'JOB-NEW-001',
            'status': JobStatusChoices.DRAFT,
            'employment_type': 'full_time',
            'headcount': 1,
        }

        response = authenticated_client.post(url, data)

        # 求人が作成されたことを確認
        assert Job.objects.filter(unique_code='JOB-NEW-001').exists()
        job = Job.objects.get(unique_code='JOB-NEW-001')
        assert job.tenant == tenant
        assert job.created_by == admin_user


class TestJobUpdateView:
    """求人更新ビューテスト"""

    @pytest.mark.django_db
    def test_form_valid_updates_job(self, authenticated_client, active_job):
        """フォーム送信で求人が更新される"""
        url = reverse('jobs:job_update', kwargs={'pk': active_job.pk})
        data = {
            'title': '更新後の求人タイトル',
            'unique_code': active_job.unique_code,
            'status': active_job.status,
            'employment_type': 'full_time',
            'headcount': 2,
        }

        response = authenticated_client.post(url, data)

        # 求人が更新されたことを確認
        active_job.refresh_from_db()
        assert active_job.title == '更新後の求人タイトル'
        assert active_job.headcount == 2


class TestJobDuplicateView:
    """求人複製ビューテスト"""

    @pytest.mark.django_db
    def test_duplicate_with_existing_code(self, authenticated_client, tenant, admin_user):
        """既存コードがある場合のユニークコード生成"""
        # 元の求人を作成
        original = Job.objects.create(
            tenant=tenant,
            title='元の求人',
            unique_code='ORIG-001',
            status=JobStatusChoices.ACTIVE,
            created_by=admin_user,
        )

        # コピーを作成（これで ORIG-001_copy1 ができる）
        Job.objects.create(
            tenant=tenant,
            title='コピー1',
            unique_code='ORIG-001_copy1',
            status=JobStatusChoices.DRAFT,
            created_by=admin_user,
        )

        # 複製を実行
        url = reverse('jobs:job_duplicate', kwargs={'pk': original.pk})
        response = authenticated_client.post(url)

        # ORIG-001_copy2 が生成されることを確認
        assert Job.objects.filter(unique_code='ORIG-001_copy2').exists()


# =============================================================================
# Application View Tests
# =============================================================================

class TestApplicationCreateView:
    """応募作成ビューテスト"""

    @pytest.mark.django_db
    def test_form_valid_creates_application(self, authenticated_client, tenant, candidate, active_job):
        """フォーム送信で応募が作成される"""
        url = reverse('applications:application_create')
        data = {
            'candidate': candidate.pk,
            'job': active_job.pk,
            'status': ApplicationStatusChoices.NEW,
        }

        response = authenticated_client.post(url, data)

        # 応募が作成されたことを確認
        assert Application.objects.filter(candidate=candidate, job=active_job).exists()


# =============================================================================
# Interview View Tests
# =============================================================================
# Note: InterviewCreateView と InterviewUpdateView のテストは
# フォームの複雑性により他のテストファイルで詳細にカバーされています。

class TestInterviewResultView:
    """面接結果入力ビューテスト"""

    @pytest.mark.django_db
    def test_invalid_result_shows_error(self, authenticated_client, interview):
        """無効な結果でエラーメッセージ表示"""
        url = reverse('interviews:interview_result', kwargs={'pk': interview.pk})
        data = {
            'result': 'invalid_result',  # 無効な結果
            'evaluation_score': 4,
            'feedback': 'テストフィードバック',
        }

        response = authenticated_client.post(url, data)

        # エラーメッセージが表示されることを確認
        messages = list(get_messages(response.wsgi_request))
        assert any('無効な結果' in str(m) for m in messages)


# =============================================================================
# Candidate View Tests
# =============================================================================

class TestCandidateCreateView:
    """候補者作成ビューテスト"""

    @pytest.mark.django_db
    def test_form_valid_creates_candidate(self, authenticated_client, tenant, admin_user):
        """フォーム送信で候補者が作成される"""
        url = reverse('candidates:candidate_create')
        data = {
            'name': '新規候補者',
            'email': 'new-candidate@view-test.com',
            'gender': 'unspecified',
            'employment_status': 'employed',
        }

        response = authenticated_client.post(url, data)

        # 候補者が作成されたことを確認
        assert Candidate.objects.filter(email='new-candidate@view-test.com').exists()
        candidate = Candidate.objects.get(email='new-candidate@view-test.com')
        assert candidate.tenant == tenant
        assert candidate.registered_by == admin_user


class TestCandidateUpdateView:
    """候補者更新ビューテスト"""

    @pytest.mark.django_db
    def test_form_valid_updates_candidate(self, authenticated_client, candidate):
        """フォーム送信で候補者が更新される"""
        url = reverse('candidates:candidate_update', kwargs={'pk': candidate.pk})
        data = {
            'name': '更新後の候補者名',
            'email': candidate.email,
            'gender': 'male',
            'employment_status': 'employed',
        }

        response = authenticated_client.post(url, data)

        # 候補者が更新されたことを確認
        candidate.refresh_from_db()
        assert candidate.name == '更新後の候補者名'
