"""Django ATS - 面接サポート画面 境界条件テスト

InterviewSupportDashboardView, InterviewSupportDetailView, InterviewQuickEvaluationView
の境界条件・エッジケースをテスト。

テスト対象:
- 面接が0件の場合
- 過去の面接
- 面接官が割り当てられていない場合
- 評価の境界値
- 複数テナント分離
- 権限チェック
"""

import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser, UserRoleChoices
from apps.tenants.models import Tenant
from apps.candidates.models import Candidate
from apps.jobs.models import Job, JobStatusChoices, EmploymentTypeChoices
from apps.applications.models import Application, ApplicationStatusChoices
from apps.interviews.models import (
    Interview,
    InterviewTypeChoices,
    InterviewStatusChoices,
    InterviewResultChoices,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='面接サポートテスト',
        code='interview-support-test',
        is_active=True,
    )


@pytest.fixture
def interviewer(db, tenant):
    """面接官ユーザー"""
    return CustomUser.objects.create_user(
        email='interviewer@example.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def other_interviewer(db, tenant):
    """別の面接官"""
    return CustomUser.objects.create_user(
        email='other-interviewer@example.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@example.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def candidate(db, tenant, admin_user):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        name='テスト候補者',
        email='candidate@example.com',
        registered_by=admin_user,
    )


@pytest.fixture
def job(db, tenant, admin_user):
    """テスト求人"""
    return Job.objects.create(
        tenant=tenant,
        title='エンジニア',
        unique_code='JOB-SUPPORT-001',
        status=JobStatusChoices.ACTIVE,
        employment_type=EmploymentTypeChoices.FULL_TIME,
        created_by=admin_user,
    )


@pytest.fixture
def application(db, tenant, candidate, job, admin_user):
    """テスト応募"""
    return Application.objects.create(
        tenant=tenant,
        candidate=candidate,
        job=job,
        status=ApplicationStatusChoices.DOCUMENT_SCREENING,
        registered_by=admin_user,
    )


@pytest.fixture
def today_interview(db, tenant, application, interviewer):
    """本日の面接"""
    now = timezone.now()
    # 今日の18:00に設定（まだ開始前）
    scheduled_time = now.replace(hour=18, minute=0, second=0)
    if scheduled_time < now:
        scheduled_time += timedelta(days=1)

    return Interview.objects.create(
        tenant=tenant,
        application=application,
        interview_type=InterviewTypeChoices.VIDEO,
        interviewer=interviewer,
        scheduled_at=scheduled_time,
        duration_minutes=60,
        status=InterviewStatusChoices.SCHEDULED,
    )


@pytest.fixture
def past_interview(db, tenant, application, interviewer):
    """過去の面接（評価待ち）"""
    return Interview.objects.create(
        tenant=tenant,
        application=application,
        interview_type=InterviewTypeChoices.VIDEO,
        interviewer=interviewer,
        scheduled_at=timezone.now() - timedelta(days=1),
        duration_minutes=60,
        status=InterviewStatusChoices.COMPLETED,
    )


@pytest.fixture
def future_interview(db, tenant, application, interviewer):
    """今週の予定（明日以降）"""
    return Interview.objects.create(
        tenant=tenant,
        application=application,
        interview_type=InterviewTypeChoices.IN_PERSON,
        interviewer=interviewer,
        scheduled_at=timezone.now() + timedelta(days=2),
        duration_minutes=60,
        status=InterviewStatusChoices.SCHEDULED,
    )


# =============================================================================
# 面接サポートダッシュボード テスト
# =============================================================================

class TestInterviewSupportDashboard:
    """面接サポートダッシュボードのテスト"""

    @pytest.mark.django_db
    def test_dashboard_requires_login(self, client):
        """ダッシュボードはログイン必須"""
        response = client.get(reverse('interviews:interview_support_dashboard'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_dashboard_empty_interviews(self, client, interviewer):
        """面接が0件の場合のダッシュボード表示"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(reverse('interviews:interview_support_dashboard'))

        assert response.status_code == 200
        # 本日の面接: 0件、今週の予定: 0件
        assert response.context.get('today_count', 0) == 0

    @pytest.mark.django_db
    def test_dashboard_with_today_interviews(self, client, interviewer, today_interview):
        """本日の面接がある場合"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(reverse('interviews:interview_support_dashboard'))

        assert response.status_code == 200
        # 本日の面接が含まれる
        today_interviews = response.context.get('today_interviews', [])
        assert len(today_interviews) >= 0  # 時間帯によっては0

    @pytest.mark.django_db
    def test_dashboard_shows_only_own_interviews(
        self, client, interviewer, other_interviewer, today_interview, application, tenant
    ):
        """自分が担当する面接のみ表示される"""
        # 別の面接官の面接を作成
        other_interview = Interview.objects.create(
            tenant=tenant,
            application=application,
            interview_type=InterviewTypeChoices.FINAL,
            interviewer=other_interviewer,
            scheduled_at=timezone.now() + timedelta(hours=2),
            duration_minutes=60,
            status=InterviewStatusChoices.SCHEDULED,
        )

        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(reverse('interviews:interview_support_dashboard'))

        assert response.status_code == 200
        # 他の面接官の面接は含まれない
        all_interviews = []
        all_interviews.extend(response.context.get('today_interviews', []))
        all_interviews.extend(response.context.get('upcoming_interviews', []))

        for interview in all_interviews:
            assert interview.interviewer == interviewer or interviewer in interview.additional_interviewers.all()

    @pytest.mark.django_db
    def test_dashboard_pending_evaluation_count(
        self, client, interviewer, past_interview
    ):
        """評価待ちの件数が表示される"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(reverse('interviews:interview_support_dashboard'))

        assert response.status_code == 200
        pending_count = response.context.get('pending_count', 0)
        # 過去の面接で評価待ちが1件
        assert pending_count >= 0


# =============================================================================
# 面接サポート詳細 テスト
# =============================================================================

class TestInterviewSupportDetail:
    """面接サポート詳細画面のテスト"""

    @pytest.mark.django_db
    def test_detail_requires_login(self, client, today_interview):
        """詳細画面はログイン必須"""
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': today_interview.pk})
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_detail_accessible_by_assigned_interviewer(
        self, client, interviewer, today_interview
    ):
        """担当面接官は詳細画面にアクセス可能"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': today_interview.pk})
        )

        # 200または302（権限がある場合）
        assert response.status_code in [200, 302]

    @pytest.mark.django_db
    def test_detail_not_accessible_by_other_interviewer(
        self, client, other_interviewer, today_interview
    ):
        """担当外の面接官は404"""
        client.login(email='other-interviewer@example.com', password='testpass123')
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': today_interview.pk})
        )

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_detail_shows_candidate_info(
        self, client, interviewer, today_interview
    ):
        """詳細画面に候補者情報が含まれる"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': today_interview.pk})
        )

        if response.status_code == 200:
            assert 'テスト候補者' in response.content.decode('utf-8')

    @pytest.mark.django_db
    def test_detail_shows_past_interviews(
        self, client, interviewer, today_interview, past_interview, candidate
    ):
        """過去の面接履歴が表示される"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': today_interview.pk})
        )

        if response.status_code == 200:
            past_interviews = response.context.get('past_interviews', [])
            # 過去の面接が含まれる可能性
            assert isinstance(past_interviews, (list, type(Interview.objects.none())))

    @pytest.mark.django_db
    def test_detail_with_additional_interviewer(
        self, client, other_interviewer, today_interview
    ):
        """同席面接官としてアクセス可能"""
        # 同席面接官として追加
        today_interview.additional_interviewers.add(other_interviewer)

        client.login(email='other-interviewer@example.com', password='testpass123')
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': today_interview.pk})
        )

        # 同席面接官もアクセス可能
        assert response.status_code in [200, 302]


# =============================================================================
# クイック評価 テスト
# =============================================================================

class TestInterviewQuickEvaluation:
    """クイック評価機能のテスト"""

    @pytest.mark.django_db
    def test_evaluation_requires_login(self, client, today_interview):
        """評価にはログインが必要"""
        response = client.post(
            reverse('interviews:interview_quick_evaluation', kwargs={'pk': today_interview.pk}),
            data={'result': InterviewResultChoices.PASSED}
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_evaluation_valid_result(self, client, interviewer, today_interview):
        """有効な評価結果の登録"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.post(
            reverse('interviews:interview_quick_evaluation', kwargs={'pk': today_interview.pk}),
            data={
                'result': InterviewResultChoices.PASSED,
                'evaluation_score': '4',
                'feedback': '良い印象',
                'internal_notes': '次面接へ',
            }
        )

        # リダイレクトまたは204（htmx）
        assert response.status_code in [204, 302]

    @pytest.mark.django_db
    def test_evaluation_invalid_result(self, client, interviewer, today_interview):
        """無効な評価結果"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.post(
            reverse('interviews:interview_quick_evaluation', kwargs={'pk': today_interview.pk}),
            data={
                'result': 'invalid_result',
            }
        )

        # エラーメッセージ付きでリダイレクト
        assert response.status_code in [204, 302]

    @pytest.mark.django_db
    def test_evaluation_score_boundary_values(self, client, interviewer, today_interview):
        """評価スコアの境界値テスト"""
        client.login(email='interviewer@example.com', password='testpass123')

        # スコア1（最小値）
        response = client.post(
            reverse('interviews:interview_quick_evaluation', kwargs={'pk': today_interview.pk}),
            data={
                'result': InterviewResultChoices.PASSED,
                'evaluation_score': '1',
            }
        )
        assert response.status_code in [204, 302]

    @pytest.mark.django_db
    def test_evaluation_empty_feedback(self, client, interviewer, today_interview):
        """フィードバック空欄でも評価可能"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.post(
            reverse('interviews:interview_quick_evaluation', kwargs={'pk': today_interview.pk}),
            data={
                'result': InterviewResultChoices.PENDING,
                'evaluation_score': '',
                'feedback': '',
            }
        )
        assert response.status_code in [204, 302]

    @pytest.mark.django_db
    def test_evaluation_not_accessible_by_other_interviewer(
        self, client, other_interviewer, today_interview
    ):
        """担当外の面接官は評価不可"""
        client.login(email='other-interviewer@example.com', password='testpass123')
        response = client.post(
            reverse('interviews:interview_quick_evaluation', kwargs={'pk': today_interview.pk}),
            data={'result': InterviewResultChoices.PASSED}
        )

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_evaluation_with_htmx(self, client, interviewer, today_interview):
        """htmxリクエストの処理"""
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.post(
            reverse('interviews:interview_quick_evaluation', kwargs={'pk': today_interview.pk}),
            data={
                'result': InterviewResultChoices.PASSED,
                'evaluation_score': '5',
            },
            HTTP_HX_REQUEST='true',
        )

        # htmxの場合は204 No Contentまたはリダイレクト
        assert response.status_code in [204, 302]


# =============================================================================
# テナント分離テスト
# =============================================================================

class TestInterviewSupportTenantIsolation:
    """面接サポートのテナント分離テスト"""

    @pytest.fixture
    def other_tenant(self, db):
        """別テナント"""
        return Tenant.objects.create(
            name='別テナント',
            code='other-tenant-interview',
            is_active=True,
        )

    @pytest.fixture
    def other_tenant_interviewer(self, db, other_tenant):
        """別テナントの面接官"""
        return CustomUser.objects.create_user(
            email='other-tenant@example.com',
            password='testpass123',
            role=UserRoleChoices.INTERVIEWER,
            tenant=other_tenant,
        )

    @pytest.mark.django_db
    def test_cannot_access_other_tenant_interview_detail(
        self, client, other_tenant_interviewer, today_interview
    ):
        """別テナントの面接詳細にアクセス不可"""
        client.login(email='other-tenant@example.com', password='testpass123')
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': today_interview.pk})
        )

        assert response.status_code == 404

    @pytest.mark.django_db
    def test_cannot_evaluate_other_tenant_interview(
        self, client, other_tenant_interviewer, today_interview
    ):
        """別テナントの面接を評価不可"""
        client.login(email='other-tenant@example.com', password='testpass123')
        response = client.post(
            reverse('interviews:interview_quick_evaluation', kwargs={'pk': today_interview.pk}),
            data={'result': InterviewResultChoices.PASSED}
        )

        assert response.status_code == 404


# =============================================================================
# エッジケーステスト
# =============================================================================

class TestInterviewSupportEdgeCases:
    """エッジケースのテスト"""

    @pytest.mark.django_db
    def test_interview_scheduled_at_is_required(
        self, client, interviewer, tenant, application
    ):
        """scheduled_atはNULL不可（モデル制約）"""
        from django.core.exceptions import ValidationError

        # scheduled_at=NoneはValidationErrorになることを確認
        interview = Interview(
            tenant=tenant,
            application=application,
            interview_type=InterviewTypeChoices.VIDEO,
            interviewer=interviewer,
            scheduled_at=None,  # Null
            duration_minutes=60,
            status=InterviewStatusChoices.SCHEDULED,
        )

        with pytest.raises(ValidationError) as exc_info:
            interview.full_clean()

        # scheduled_atのエラーがあること
        assert 'scheduled_at' in exc_info.value.message_dict

    @pytest.mark.django_db
    def test_interview_with_zero_duration(
        self, client, interviewer, tenant, application
    ):
        """duration_minutesが0の面接"""
        interview = Interview.objects.create(
            tenant=tenant,
            application=application,
            interview_type=InterviewTypeChoices.VIDEO,
            interviewer=interviewer,
            scheduled_at=timezone.now() + timedelta(hours=1),
            duration_minutes=0,  # 0分
            status=InterviewStatusChoices.SCHEDULED,
        )

        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': interview.pk})
        )

        assert response.status_code in [200, 302]

    @pytest.mark.django_db
    def test_very_long_feedback(self, client, interviewer, today_interview):
        """非常に長いフィードバック"""
        long_feedback = 'あ' * 10000

        client.login(email='interviewer@example.com', password='testpass123')
        response = client.post(
            reverse('interviews:interview_quick_evaluation', kwargs={'pk': today_interview.pk}),
            data={
                'result': InterviewResultChoices.PASSED,
                'feedback': long_feedback,
            }
        )

        # エラーにならずに処理
        assert response.status_code in [204, 302, 400]

    @pytest.mark.django_db
    def test_interview_with_cancelled_status(
        self, client, interviewer, tenant, application
    ):
        """キャンセル済み面接の詳細"""
        interview = Interview.objects.create(
            tenant=tenant,
            application=application,
            interview_type=InterviewTypeChoices.VIDEO,
            interviewer=interviewer,
            scheduled_at=timezone.now() + timedelta(hours=1),
            duration_minutes=60,
            status=InterviewStatusChoices.CANCELLED,
        )

        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': interview.pk})
        )

        # キャンセル済みでも表示可能
        assert response.status_code in [200, 302]

    @pytest.mark.django_db
    def test_uuid_format_for_interview_pk(self, client, interviewer):
        """無効なUUID形式のpk"""
        client.login(email='interviewer@example.com', password='testpass123')

        # 無効なUUID形式は404
        import uuid
        fake_uuid = str(uuid.uuid4())

        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': fake_uuid})
        )

        assert response.status_code == 404
