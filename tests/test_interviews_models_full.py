"""Django ATS - 面接モデル完全カバレッジテスト

interviews/models.pyの100%カバレッジを目指すテスト。
"""

import pytest
from datetime import timedelta
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices
from apps.candidates.models import Candidate
from apps.jobs.models import Job, JobStatusChoices
from apps.applications.models import Application, ApplicationStatusChoices
from apps.interviews.models import (
    Interview, InterviewStatusChoices, InterviewTypeChoices,
    InterviewResultChoices, InterviewFeedbackRequest
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='面接モデルテスト',
        code='interview-model-test',
        is_active=True,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@interview-model-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def interviewer(db, tenant):
    """面接官"""
    return CustomUser.objects.create_user(
        email='interviewer@interview-model-test.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def feedback_user(db, tenant):
    """フィードバック依頼先ユーザー"""
    return CustomUser.objects.create_user(
        email='feedback@interview-model-test.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def candidate(db, tenant, admin_user):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        email='candidate@interview-model-test.com',
        name='テスト候補者',
        registered_by=admin_user,
    )


@pytest.fixture
def job(db, tenant, admin_user):
    """テスト求人"""
    return Job.objects.create(
        tenant=tenant,
        title='テスト求人',
        unique_code='JOB-INT-MODEL-001',
        status=JobStatusChoices.ACTIVE,
        created_by=admin_user,
    )


@pytest.fixture
def application(db, tenant, candidate, job):
    """テスト応募"""
    return Application.objects.create(
        tenant=tenant,
        candidate=candidate,
        job=job,
        status=ApplicationStatusChoices.INTERVIEWING,
    )


@pytest.fixture
def interview(db, tenant, application, interviewer):
    """テスト面接"""
    return Interview.objects.create(
        tenant=tenant,
        application=application,
        interviewer=interviewer,
        interview_type=InterviewTypeChoices.VIDEO,
        scheduled_at=timezone.now() + timedelta(days=1),
        status=InterviewStatusChoices.SCHEDULED,
    )


@pytest.fixture
def final_interview(db, tenant, application, interviewer):
    """最終面接"""
    return Interview.objects.create(
        tenant=tenant,
        application=application,
        interviewer=interviewer,
        interview_type=InterviewTypeChoices.FINAL,
        scheduled_at=timezone.now() + timedelta(days=7),
        status=InterviewStatusChoices.SCHEDULED,
    )


@pytest.fixture
def completed_interview(db, tenant, application, interviewer):
    """完了済み面接（時間記録あり）"""
    now = timezone.now()
    return Interview.objects.create(
        tenant=tenant,
        application=application,
        interviewer=interviewer,
        interview_type=InterviewTypeChoices.IN_PERSON,
        scheduled_at=now - timedelta(hours=2),
        started_at=now - timedelta(hours=1, minutes=30),
        ended_at=now - timedelta(hours=1),
        status=InterviewStatusChoices.COMPLETED,
        result=InterviewResultChoices.PASSED,
    )


# =============================================================================
# Interview Model Property Tests
# =============================================================================

class TestInterviewModelProperties:
    """Interviewモデルプロパティテスト"""

    @pytest.mark.django_db
    def test_get_absolute_url(self, interview):
        """get_absolute_urlメソッド"""
        url = interview.get_absolute_url()
        assert str(interview.pk) in url
        assert '/interviews/' in url

    @pytest.mark.django_db
    def test_get_interview_round_display_regular(self, interview):
        """面接回数表示（通常）"""
        result = interview.get_interview_round_display()
        assert '次面接' in result

    @pytest.mark.django_db
    def test_get_interview_round_display_final(self, final_interview):
        """面接回数表示（最終面接）"""
        result = final_interview.get_interview_round_display()
        assert result == '最終面接'

    @pytest.mark.django_db
    def test_is_upcoming_true(self, interview):
        """今後の面接（該当）"""
        assert interview.is_upcoming is True

    @pytest.mark.django_db
    def test_is_upcoming_false_past(self, tenant, application, interviewer):
        """今後の面接（過去）"""
        past_interview = Interview.objects.create(
            tenant=tenant,
            application=application,
            interviewer=interviewer,
            interview_type=InterviewTypeChoices.PHONE,
            scheduled_at=timezone.now() - timedelta(days=1),
            status=InterviewStatusChoices.SCHEDULED,
        )
        assert past_interview.is_upcoming is False

    @pytest.mark.django_db
    def test_is_upcoming_false_completed(self, completed_interview):
        """今後の面接（完了済み）"""
        assert completed_interview.is_upcoming is False

    @pytest.mark.django_db
    def test_is_today_true(self, tenant, application, interviewer):
        """今日の面接（該当）"""
        today_interview = Interview.objects.create(
            tenant=tenant,
            application=application,
            interviewer=interviewer,
            interview_type=InterviewTypeChoices.VIDEO,
            scheduled_at=timezone.now(),
            status=InterviewStatusChoices.SCHEDULED,
        )
        assert today_interview.is_today is True

    @pytest.mark.django_db
    def test_is_today_false(self, interview):
        """今日の面接（非該当）"""
        # interviewは明日予定
        assert interview.is_today is False

    @pytest.mark.django_db
    def test_candidate_property(self, interview, candidate):
        """候補者ショートカット"""
        assert interview.candidate == candidate

    @pytest.mark.django_db
    def test_job_property(self, interview, job):
        """求人ショートカット"""
        assert interview.job == job

    @pytest.mark.django_db
    def test_actual_duration_minutes_with_times(self, completed_interview):
        """実際の面接時間（時間記録あり）"""
        duration = completed_interview.actual_duration_minutes
        assert duration is not None
        # 30分の面接
        assert duration == 30

    @pytest.mark.django_db
    def test_actual_duration_minutes_without_times(self, interview):
        """実際の面接時間（時間記録なし）"""
        assert interview.actual_duration_minutes is None

    @pytest.mark.django_db
    def test_actual_duration_minutes_started_only(self, tenant, application, interviewer):
        """実際の面接時間（開始のみ記録）"""
        interview = Interview.objects.create(
            tenant=tenant,
            application=application,
            interviewer=interviewer,
            interview_type=InterviewTypeChoices.VIDEO,
            scheduled_at=timezone.now(),
            started_at=timezone.now(),
            status=InterviewStatusChoices.SCHEDULED,
        )
        assert interview.actual_duration_minutes is None


# =============================================================================
# Interview Model Method Tests
# =============================================================================

class TestInterviewModelMethods:
    """Interviewモデルメソッドテスト"""

    @pytest.mark.django_db
    def test_complete(self, interview):
        """面接完了"""
        interview.complete(
            result=InterviewResultChoices.PASSED,
            score=85,
            feedback='良い面接でした',
            internal_notes='採用推奨'
        )

        interview.refresh_from_db()
        assert interview.status == InterviewStatusChoices.COMPLETED
        assert interview.result == InterviewResultChoices.PASSED
        assert interview.evaluation_score == 85
        assert interview.feedback == '良い面接でした'
        assert interview.internal_notes == '採用推奨'
        assert interview.ended_at is not None

    @pytest.mark.django_db
    def test_complete_with_existing_ended_at(self, tenant, application, interviewer):
        """面接完了（終了時刻既存）"""
        now = timezone.now()
        interview = Interview.objects.create(
            tenant=tenant,
            application=application,
            interviewer=interviewer,
            interview_type=InterviewTypeChoices.VIDEO,
            scheduled_at=now - timedelta(hours=1),
            started_at=now - timedelta(minutes=45),
            ended_at=now - timedelta(minutes=15),
            status=InterviewStatusChoices.SCHEDULED,
        )
        original_ended_at = interview.ended_at

        interview.complete(
            result=InterviewResultChoices.PASSED,
            score=90
        )

        interview.refresh_from_db()
        # 既存のended_atは変更されない
        assert interview.ended_at == original_ended_at

    @pytest.mark.django_db
    def test_cancel(self, interview):
        """面接キャンセル"""
        interview.cancel(reason='候補者の都合')

        interview.refresh_from_db()
        assert interview.status == InterviewStatusChoices.CANCELLED
        assert interview.internal_notes == '候補者の都合'


# =============================================================================
# InterviewFeedbackRequest Model Tests
# =============================================================================

class TestInterviewFeedbackRequestModel:
    """InterviewFeedbackRequestモデルテスト"""

    @pytest.fixture
    def feedback_request(self, db, tenant, interview, feedback_user):
        """フィードバック依頼"""
        return InterviewFeedbackRequest.objects.create(
            tenant=tenant,
            interview=interview,
            requested_to=feedback_user,
        )

    @pytest.mark.django_db
    def test_str(self, feedback_request):
        """__str__メソッド"""
        result = str(feedback_request)
        # 面接情報とユーザー情報が含まれる
        assert 'feedback@interview-model-test.com' in result

    @pytest.mark.django_db
    def test_submit(self, feedback_request):
        """フィードバック提出"""
        feedback_request.submit(
            score=80,
            feedback='良い印象でした'
        )

        feedback_request.refresh_from_db()
        assert feedback_request.evaluation_score == 80
        assert feedback_request.feedback == '良い印象でした'
        assert feedback_request.is_completed is True
        assert feedback_request.completed_at is not None
