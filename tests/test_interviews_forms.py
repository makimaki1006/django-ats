"""Django ATS - 面接フォームテスト

面接関連フォームのテスト。
"""

import pytest
from datetime import datetime, timedelta
from django.utils import timezone

from apps.interviews.forms import InterviewForm, InterviewFilterForm, InterviewResultForm
from apps.interviews.models import Interview, InterviewStatusChoices, InterviewResultChoices
from apps.applications.models import Application, ApplicationStatusChoices
from apps.candidates.models import Candidate
from apps.jobs.models import Job, JobStatusChoices
from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='面接フォームテスト',
        code='interview-form-test',
        is_active=True,
    )


@pytest.fixture
def other_tenant(db):
    """別テナント"""
    return Tenant.objects.create(
        name='別テナント',
        code='other-tenant',
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """テストユーザー（面接官）"""
    return CustomUser.objects.create_user(
        email='interviewer@form-test.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@form-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def other_user(db, other_tenant):
    """別テナントのユーザー"""
    return CustomUser.objects.create_user(
        email='other@other-tenant.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=other_tenant,
    )


@pytest.fixture
def candidate(db, tenant):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        email='candidate@test.com',
        name='山田太郎',
    )


@pytest.fixture
def job(db, tenant, admin_user):
    """テスト求人"""
    return Job.objects.create(
        tenant=tenant,
        title='ソフトウェアエンジニア',
        unique_code='JOB-001',
        status=JobStatusChoices.ACTIVE,
        created_by=admin_user,
    )


@pytest.fixture
def other_job(db, other_tenant, other_user):
    """別テナントの求人"""
    return Job.objects.create(
        tenant=other_tenant,
        title='別求人',
        unique_code='OTHER-JOB-001',
        status=JobStatusChoices.ACTIVE,
        created_by=other_user,
    )


@pytest.fixture
def application(db, tenant, candidate, job):
    """テスト応募"""
    return Application.objects.create(
        tenant=tenant,
        candidate=candidate,
        job=job,
        status=ApplicationStatusChoices.NEW,
    )


@pytest.fixture
def other_application(db, other_tenant, other_job):
    """別テナントの応募"""
    other_candidate = Candidate.objects.create(
        tenant=other_tenant,
        email='other-candidate@test.com',
        name='佐藤次郎',
    )
    return Application.objects.create(
        tenant=other_tenant,
        candidate=other_candidate,
        job=other_job,
        status=ApplicationStatusChoices.NEW,
    )


# =============================================================================
# InterviewForm Tests
# =============================================================================

class TestInterviewForm:
    """InterviewForm のテスト"""

    @pytest.mark.django_db
    def test_form_without_tenant(self):
        """テナントなしでもフォームは作成可能"""
        form = InterviewForm()
        # フォームのフィールドが存在することを確認
        assert 'application' in form.fields
        assert 'interview_type' in form.fields
        assert 'interviewer' in form.fields

    @pytest.mark.django_db
    def test_form_with_tenant_filters_applications(self, tenant, application, other_application):
        """テナント指定で応募がフィルタリングされる"""
        form = InterviewForm(tenant=tenant)
        queryset = form.fields['application'].queryset

        assert application in queryset
        assert other_application not in queryset

    @pytest.mark.django_db
    def test_form_with_tenant_filters_interviewers(self, tenant, user, admin_user, other_user):
        """テナント指定で面接官がフィルタリングされる"""
        form = InterviewForm(tenant=tenant)
        interviewer_queryset = form.fields['interviewer'].queryset
        additional_queryset = form.fields['additional_interviewers'].queryset

        # 同じテナントのユーザーが含まれる
        assert user in interviewer_queryset
        assert admin_user in interviewer_queryset

        # 別テナントのユーザーは含まれない
        assert other_user not in interviewer_queryset
        assert other_user not in additional_queryset

    @pytest.mark.django_db
    def test_form_inactive_users_excluded(self, tenant, user):
        """非アクティブユーザーは面接官から除外される"""
        inactive_user = CustomUser.objects.create_user(
            email='inactive@form-test.com',
            password='testpass123',
            role=UserRoleChoices.INTERVIEWER,
            tenant=tenant,
            is_active=False,
        )

        form = InterviewForm(tenant=tenant)
        queryset = form.fields['interviewer'].queryset

        assert user in queryset
        assert inactive_user not in queryset


# =============================================================================
# InterviewFilterForm Tests
# =============================================================================

class TestInterviewFilterForm:
    """InterviewFilterForm のテスト"""

    @pytest.mark.django_db
    def test_filter_form_empty(self):
        """空のフィルタフォームは有効"""
        form = InterviewFilterForm(data={})
        assert form.is_valid()

    @pytest.mark.django_db
    def test_filter_form_with_query(self):
        """検索クエリ付きフォーム"""
        form = InterviewFilterForm(data={'q': '山田'})
        assert form.is_valid()
        assert form.cleaned_data['q'] == '山田'

    @pytest.mark.django_db
    def test_filter_form_with_status(self):
        """ステータスフィルタ"""
        form = InterviewFilterForm(data={'status': InterviewStatusChoices.SCHEDULED})
        assert form.is_valid()
        assert form.cleaned_data['status'] == InterviewStatusChoices.SCHEDULED

    @pytest.mark.django_db
    def test_filter_form_with_date_filter(self):
        """日付フィルタ"""
        form = InterviewFilterForm(data={'date_filter': 'today'})
        assert form.is_valid()
        assert form.cleaned_data['date_filter'] == 'today'

    @pytest.mark.django_db
    def test_filter_form_date_filter_choices(self):
        """日付フィルタの選択肢"""
        for value in ['', 'today', 'week', 'upcoming']:
            form = InterviewFilterForm(data={'date_filter': value})
            assert form.is_valid()

    @pytest.mark.django_db
    def test_filter_form_all_filters(self):
        """全フィルタ組み合わせ"""
        form = InterviewFilterForm(data={
            'q': 'テスト',
            'status': InterviewStatusChoices.COMPLETED,
            'date_filter': 'week',
        })
        assert form.is_valid()


# =============================================================================
# InterviewResultForm Tests
# =============================================================================

class TestInterviewResultForm:
    """InterviewResultForm のテスト"""

    @pytest.mark.django_db
    def test_result_form_valid(self):
        """有効な結果フォーム"""
        form = InterviewResultForm(data={
            'result': InterviewResultChoices.PASSED,
            'evaluation_score': '4',
            'feedback': '良い面接でした。',
            'internal_notes': '次回面接へ進む',
        })
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_result_form_required_field(self):
        """結果は必須"""
        form = InterviewResultForm(data={})
        assert not form.is_valid()
        assert 'result' in form.errors

    @pytest.mark.django_db
    def test_result_form_optional_fields(self):
        """評価スコア・フィードバックはオプション"""
        form = InterviewResultForm(data={
            'result': InterviewResultChoices.FAILED,
        })
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_result_form_all_results(self):
        """すべての結果選択肢が有効"""
        for result_value, _ in InterviewResultChoices.choices:
            form = InterviewResultForm(data={'result': result_value})
            assert form.is_valid(), f"Result {result_value} should be valid"

    @pytest.mark.django_db
    def test_result_form_all_scores(self):
        """すべての評価スコアが有効"""
        for score in ['', '1', '2', '3', '4', '5']:
            form = InterviewResultForm(data={
                'result': InterviewResultChoices.PASSED,
                'evaluation_score': score,
            })
            assert form.is_valid(), f"Score {score} should be valid"
