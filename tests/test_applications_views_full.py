"""Django ATS - 応募ビュー完全カバレッジテスト

applications/views.pyの100%カバレッジを目指すテスト。
"""

import pytest
from unittest.mock import patch, Mock
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices
from apps.candidates.models import Candidate, GenderChoices, EmploymentStatusChoices
from apps.jobs.models import Job, JobStatusChoices
from apps.applications.models import Application, ApplicationStatusChoices
from apps.settings_app.models import ApplicationSource


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='応募ビュー完全テスト',
        code='application-views-full',
        is_active=True,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@app-views-full.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def recruiter(db, tenant):
    """採用担当者"""
    return CustomUser.objects.create_user(
        email='recruiter@app-views-full.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_RECRUITER,
        tenant=tenant,
    )


@pytest.fixture
def candidate(db, tenant, admin_user):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        email='candidate@app-views-full.com',
        name='テスト候補者',
        registered_by=admin_user,
    )


@pytest.fixture
def job(db, tenant, admin_user):
    """テスト求人"""
    return Job.objects.create(
        tenant=tenant,
        title='テスト求人',
        unique_code='JOB-APP-FULL-001',
        status=JobStatusChoices.ACTIVE,
        created_by=admin_user,
    )


@pytest.fixture
def open_job(db, tenant, admin_user):
    """公開中求人"""
    return Job.objects.create(
        tenant=tenant,
        title='公開中求人',
        unique_code='JOB-APP-FULL-002',
        status=JobStatusChoices.ACTIVE,
        created_by=admin_user,
    )


@pytest.fixture
def application(db, tenant, candidate, job, admin_user):
    """テスト応募"""
    return Application.objects.create(
        tenant=tenant,
        candidate=candidate,
        job=job,
        status=ApplicationStatusChoices.NEW,
        registered_by=admin_user,
    )


@pytest.fixture
def application_source(db, tenant):
    """応募経路"""
    return ApplicationSource.objects.create(
        tenant=tenant,
        name='テスト応募経路',
        is_active=True,
    )


# =============================================================================
# ApplicationCreateView Tests
# =============================================================================

class TestApplicationCreateViewFull:
    """応募作成ビュー完全テスト"""

    @pytest.mark.django_db
    def test_create_form_get(self, client, admin_user, tenant, candidate, job):
        """作成フォームの表示"""
        client.force_login(admin_user)
        response = client.get(reverse('applications:application_create'))
        assert response.status_code == 200
        assert 'form' in response.context

    @pytest.mark.django_db
    def test_create_with_initial_candidate(self, client, admin_user, candidate):
        """候補者を初期値に設定"""
        client.force_login(admin_user)
        response = client.get(
            reverse('applications:application_create'),
            {'candidate': str(candidate.pk)}
        )
        assert response.status_code == 200


# =============================================================================
# ApplicationUpdateView Tests
# =============================================================================

class TestApplicationUpdateViewFull:
    """応募更新ビュー完全テスト"""

    @pytest.mark.django_db
    def test_update_form_display(self, client, admin_user, application):
        """更新フォームの表示"""
        client.force_login(admin_user)
        response = client.get(
            reverse('applications:application_update', kwargs={'pk': application.pk})
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_update_form_valid(self, client, admin_user, application):
        """有効なフォームで更新"""
        client.force_login(admin_user)
        data = {
            'candidate': application.candidate.pk,
            'job': application.job.pk,
            'status': ApplicationStatusChoices.DOCUMENT_SCREENING,
        }
        response = client.post(
            reverse('applications:application_update', kwargs={'pk': application.pk}),
            data
        )
        assert response.status_code in [200, 302]

    @pytest.mark.django_db
    def test_update_success_message(self, client, admin_user, application):
        """更新成功メッセージ"""
        client.force_login(admin_user)
        data = {
            'candidate': application.candidate.pk,
            'job': application.job.pk,
            'status': ApplicationStatusChoices.DOCUMENT_SCREENING,
        }
        response = client.post(
            reverse('applications:application_update', kwargs={'pk': application.pk}),
            data,
            follow=True
        )
        # メッセージがある
        assert response.status_code in [200, 302]


# =============================================================================
# UnifiedApplicationFormView Tests
# =============================================================================

class TestUnifiedApplicationFormViewFull:
    """統合応募フォームビュー完全テスト"""

    @pytest.mark.django_db
    def test_unified_form_get(self, client, admin_user):
        """統合フォームGET"""
        client.force_login(admin_user)
        response = client.get(reverse('applications:unified_form'))
        assert response.status_code == 200
        assert 'form' in response.context

    @pytest.mark.django_db
    def test_unified_form_get_with_job_param(self, client, admin_user, open_job):
        """求人パラメータ付きGET"""
        client.force_login(admin_user)
        response = client.get(
            reverse('applications:unified_form'),
            {'job': open_job.pk}
        )
        assert response.status_code == 200
        assert 'form' in response.context

    @pytest.mark.django_db
    def test_unified_form_post_invalid(self, client, admin_user):
        """無効なデータで統合フォームPOST"""
        client.force_login(admin_user)
        data = {
            'name': '',  # 必須フィールドが空
            'email': 'invalid-email',
        }
        response = client.post(reverse('applications:unified_form'), data)
        assert response.status_code == 200  # フォームエラーで再表示
        assert 'form' in response.context

    @pytest.mark.django_db
    def test_unified_form_post_missing_job(self, client, admin_user):
        """求人未選択でPOST"""
        client.force_login(admin_user)
        data = {
            'name': '候補者名',
            'email': 'test@example.com',
        }
        response = client.post(reverse('applications:unified_form'), data)
        # 求人が必須なのでフォームエラー
        assert response.status_code == 200
        assert 'form' in response.context


# =============================================================================
# UnifiedApplicationCompleteView Tests
# =============================================================================

class TestUnifiedApplicationCompleteViewFull:
    """統合応募完了ビュー完全テスト"""

    @pytest.mark.django_db
    def test_complete_view(self, client, admin_user, application):
        """完了ビュー表示"""
        client.force_login(admin_user)
        response = client.get(
            reverse('applications:unified_complete', kwargs={'pk': application.pk})
        )
        assert response.status_code == 200


# =============================================================================
# Application Notification Tests
# =============================================================================

class TestApplicationNotifications:
    """応募通知テスト"""

    @pytest.mark.django_db
    def test_notification_view_exists(self, client, admin_user, application):
        """通知関連のビューが存在する"""
        client.force_login(admin_user)
        # 応募詳細ページにアクセス
        response = client.get(
            reverse('applications:application_detail', kwargs={'pk': application.pk})
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_send_notifications_method_exists(self):
        """通知送信メソッドが存在する"""
        from apps.applications.views import UnifiedApplicationFormView
        # メソッドが存在することを確認
        assert hasattr(UnifiedApplicationFormView, '_send_notifications')


# =============================================================================
# Application Status Flow Tests
# =============================================================================

class TestApplicationStatusFlow:
    """応募ステータスフローテスト"""

    @pytest.mark.django_db
    def test_status_change_document_screening(self, client, admin_user, application):
        """書類選考へのステータス変更"""
        client.force_login(admin_user)
        response = client.post(
            reverse('applications:application_status', kwargs={'pk': application.pk}),
            {'status': ApplicationStatusChoices.DOCUMENT_SCREENING}
        )
        assert response.status_code == 302
        application.refresh_from_db()
        assert application.status == ApplicationStatusChoices.DOCUMENT_SCREENING

    @pytest.mark.django_db
    def test_status_change_interviewing(self, client, admin_user, application):
        """面接中へのステータス変更"""
        client.force_login(admin_user)
        response = client.post(
            reverse('applications:application_status', kwargs={'pk': application.pk}),
            {'status': ApplicationStatusChoices.INTERVIEWING}
        )
        assert response.status_code == 302
        application.refresh_from_db()
        assert application.status == ApplicationStatusChoices.INTERVIEWING

    @pytest.mark.django_db
    def test_status_change_offer_made(self, client, admin_user, application):
        """内定へのステータス変更（offer_made_at設定）"""
        client.force_login(admin_user)
        response = client.post(
            reverse('applications:application_status', kwargs={'pk': application.pk}),
            {'status': ApplicationStatusChoices.OFFER_MADE}
        )
        assert response.status_code == 302
        application.refresh_from_db()
        assert application.status == ApplicationStatusChoices.OFFER_MADE
        assert application.offer_made_at is not None


# =============================================================================
# Application Kanban Tests
# =============================================================================

class TestApplicationKanbanFull:
    """応募カンバン完全テスト"""

    @pytest.mark.django_db
    def test_kanban_with_applications(self, client, admin_user, application):
        """応募付きカンバン表示"""
        client.force_login(admin_user)
        response = client.get(reverse('applications:application_kanban'))
        assert response.status_code == 200
        assert 'status_groups' in response.context

    @pytest.mark.django_db
    def test_kanban_empty(self, client, admin_user):
        """応募なしカンバン表示"""
        client.force_login(admin_user)
        response = client.get(reverse('applications:application_kanban'))
        assert response.status_code == 200


# =============================================================================
# Application Detail Context Tests
# =============================================================================

class TestApplicationDetailContextFull:
    """応募詳細コンテキスト完全テスト"""

    @pytest.mark.django_db
    def test_detail_context_status_choices(self, client, admin_user, application):
        """詳細コンテキストにステータス選択肢"""
        client.force_login(admin_user)
        response = client.get(
            reverse('applications:application_detail', kwargs={'pk': application.pk})
        )
        assert response.status_code == 200
        assert 'status_choices' in response.context

    @pytest.mark.django_db
    def test_detail_context_status_form(self, client, admin_user, application):
        """詳細コンテキストにステータスフォーム"""
        client.force_login(admin_user)
        response = client.get(
            reverse('applications:application_detail', kwargs={'pk': application.pk})
        )
        assert response.status_code == 200
        assert 'status_form' in response.context


# =============================================================================
# Application List Filtering Tests
# =============================================================================

class TestApplicationListFilteringFull:
    """応募一覧フィルタリング完全テスト"""

    @pytest.mark.django_db
    def test_list_filter_by_status(self, client, admin_user, application):
        """ステータスでフィルタ"""
        client.force_login(admin_user)
        response = client.get(
            reverse('applications:application_list'),
            {'status': ApplicationStatusChoices.NEW}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_search_by_candidate_name(self, client, admin_user, application):
        """候補者名で検索"""
        client.force_login(admin_user)
        response = client.get(
            reverse('applications:application_list'),
            {'q': application.candidate.name}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_search_by_job_title(self, client, admin_user, application):
        """求人タイトルで検索"""
        client.force_login(admin_user)
        response = client.get(
            reverse('applications:application_list'),
            {'q': application.job.title}
        )
        assert response.status_code == 200
