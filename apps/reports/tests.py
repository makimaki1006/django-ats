"""
Django ATS - レポートアプリテスト
"""

import pytest
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.candidates.models import Candidate
from apps.jobs.models import Job, JobStatusChoices
from apps.applications.models import Application, ApplicationStatusChoices
from apps.interviews.models import Interview, InterviewStatusChoices, InterviewTypeChoices

User = get_user_model()


@pytest.fixture
def tenant(db):
    """テナントを作成"""
    return Tenant.objects.create(
        name="Test Company",
        code="test-company",
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """ユーザーを作成"""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
        tenant=tenant,
        is_active=True,
    )
    return user


@pytest.fixture
def client_logged_in(client, user, tenant):
    """ログイン済みクライアント"""
    client.login(email="test@example.com", password="testpass123")
    session = client.session
    session['tenant_id'] = str(tenant.id)
    session.save()
    return client


@pytest.fixture
def job(db, tenant, user):
    """求人を作成"""
    return Job.objects.create(
        tenant=tenant,
        unique_code="JOB001",
        title="Software Engineer",
        description="Test job description",
        status=JobStatusChoices.ACTIVE,
        created_by=user,
    )


@pytest.fixture
def candidate(db, tenant, user):
    """候補者を作成"""
    return Candidate.objects.create(
        tenant=tenant,
        name="Test Candidate",
        email="candidate@example.com",
        registered_by=user,
    )


@pytest.fixture
def application(db, tenant, job, candidate):
    """応募を作成"""
    return Application.objects.create(
        tenant=tenant,
        job=job,
        candidate=candidate,
        status=ApplicationStatusChoices.NEW,
        applied_at=timezone.now(),
    )


@pytest.fixture
def interview(db, tenant, application, user):
    """面接を作成"""
    return Interview.objects.create(
        tenant=tenant,
        application=application,
        interviewer=user,
        scheduled_at=timezone.now() + timedelta(days=1),
        interview_type=InterviewTypeChoices.VIDEO,
        status=InterviewStatusChoices.SCHEDULED,
    )


class TestReportsDashboardView:
    """レポートダッシュボードビューのテスト"""

    @pytest.mark.django_db
    def test_dashboard_requires_login(self, client):
        """未ログインユーザーはリダイレクトされる"""
        url = reverse('reports:dashboard')
        response = client.get(url)
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    @pytest.mark.django_db
    def test_dashboard_accessible(self, client_logged_in):
        """ログインユーザーはアクセス可能"""
        url = reverse('reports:dashboard')
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_dashboard_context_has_stats(self, client_logged_in, application):
        """統計情報がコンテキストに含まれる"""
        url = reverse('reports:dashboard')
        response = client_logged_in.get(url)
        assert 'stats' in response.context
        stats = response.context['stats']
        assert 'total_candidates' in stats
        assert 'total_applications' in stats
        assert 'active_jobs' in stats

    @pytest.mark.django_db
    def test_dashboard_period_filter(self, client_logged_in):
        """期間フィルターが機能する"""
        url = reverse('reports:dashboard')
        response = client_logged_in.get(url, {'period': '7'})
        assert response.status_code == 200
        assert response.context['period'] == '7'


class TestApplicationsReportView:
    """応募レポートビューのテスト"""

    @pytest.mark.django_db
    def test_applications_report_requires_login(self, client):
        """未ログインユーザーはリダイレクトされる"""
        url = reverse('reports:applications')
        response = client.get(url)
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_applications_report_accessible(self, client_logged_in):
        """ログインユーザーはアクセス可能"""
        url = reverse('reports:applications')
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_applications_report_context(self, client_logged_in, application):
        """コンテキストが正しく含まれる"""
        url = reverse('reports:applications')
        response = client_logged_in.get(url)
        assert 'weekly_applications' in response.context
        assert 'status_breakdown' in response.context
        assert 'source_breakdown' in response.context


class TestInterviewsReportView:
    """面接レポートビューのテスト"""

    @pytest.mark.django_db
    def test_interviews_report_requires_login(self, client):
        """未ログインユーザーはリダイレクトされる"""
        url = reverse('reports:interviews')
        response = client.get(url)
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_interviews_report_accessible(self, client_logged_in):
        """ログインユーザーはアクセス可能"""
        url = reverse('reports:interviews')
        response = client_logged_in.get(url)
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_interviews_report_context(self, client_logged_in, interview):
        """コンテキストが正しく含まれる"""
        url = reverse('reports:interviews')
        response = client_logged_in.get(url)
        assert 'interviewer_stats' in response.context
        assert 'type_breakdown' in response.context
        assert 'result_breakdown' in response.context


class TestExportCSVView:
    """CSVエクスポートビューのテスト"""

    @pytest.mark.django_db
    def test_export_requires_login(self, client):
        """未ログインユーザーはリダイレクトされる"""
        url = reverse('reports:export_csv', args=['candidates'])
        response = client.get(url)
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_export_candidates_csv(self, client_logged_in, candidate):
        """候補者CSVエクスポート"""
        url = reverse('reports:export_csv', args=['candidates'])
        response = client_logged_in.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv; charset=utf-8-sig'
        assert 'attachment' in response['Content-Disposition']

    @pytest.mark.django_db
    def test_export_applications_csv(self, client_logged_in, application):
        """応募CSVエクスポート"""
        url = reverse('reports:export_csv', args=['applications'])
        response = client_logged_in.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv; charset=utf-8-sig'

    @pytest.mark.django_db
    def test_export_interviews_csv(self, client_logged_in, interview):
        """面接CSVエクスポート"""
        url = reverse('reports:export_csv', args=['interviews'])
        response = client_logged_in.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv; charset=utf-8-sig'

    @pytest.mark.django_db
    def test_export_invalid_type(self, client_logged_in):
        """無効なレポートタイプはエラー"""
        url = reverse('reports:export_csv', args=['invalid'])
        response = client_logged_in.get(url)
        assert response.status_code == 400
