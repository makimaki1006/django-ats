"""Django ATS - 応募フォーム包括的テスト

applications/forms.pyの100%カバレッジを目指すテスト。
"""

import pytest
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices, Profile
from apps.candidates.models import Candidate, GenderChoices, EmploymentStatusChoices
from apps.jobs.models import Job, JobStatusChoices
from apps.applications.models import Application, ApplicationStatusChoices
from apps.applications.forms import (
    ApplicationForm,
    ApplicationFilterForm,
    ApplicationStatusForm,
    UnifiedApplicationForm,
)
from apps.settings_app.models import ApplicationSource
from apps.agents.models import AgentCompany


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='応募フォームテスト',
        code='application-form-test',
        is_active=True,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@app-form-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def agent_user(db, tenant):
    """エージェントユーザー"""
    return CustomUser.objects.create_user(
        email='agent@app-form-test.com',
        password='testpass123',
        role=UserRoleChoices.AGENT,
        tenant=tenant,
    )


@pytest.fixture
def agent_company(db, tenant):
    """エージェント会社"""
    return AgentCompany.objects.create(
        name='テストエージェント会社',
        code='AGENT-FORM-001',
        tenant=tenant,
    )


@pytest.fixture
def candidate(db, tenant, admin_user):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        email='candidate@app-form-test.com',
        name='テスト候補者',
        registered_by=admin_user,
    )


@pytest.fixture
def job(db, tenant, admin_user):
    """テスト求人"""
    return Job.objects.create(
        tenant=tenant,
        title='テスト求人',
        unique_code='JOB-FORM-001',
        status=JobStatusChoices.ACTIVE,
        created_by=admin_user,
    )


@pytest.fixture
def open_job(db, tenant, admin_user):
    """公開中求人"""
    return Job.objects.create(
        tenant=tenant,
        title='公開中求人',
        unique_code='JOB-FORM-002',
        status=JobStatusChoices.ACTIVE,
        created_by=admin_user,
    )


@pytest.fixture
def application_source(db, tenant):
    """応募経路"""
    return ApplicationSource.objects.create(
        tenant=tenant,
        name='テスト応募経路',
        is_active=True,
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


# =============================================================================
# ApplicationForm Tests
# =============================================================================

class TestApplicationFormComprehensive:
    """ApplicationForm包括テスト"""

    @pytest.mark.django_db
    def test_form_init_with_tenant(self, tenant, candidate, job, application_source):
        """テナント付きフォーム初期化"""
        form = ApplicationForm(tenant=tenant)
        assert form.tenant == tenant
        # テナントに紐づく候補者と求人のみ
        assert candidate in form.fields['candidate'].queryset

    @pytest.mark.django_db
    def test_form_clean_duplicate_check(self, tenant, candidate, job, application, admin_user):
        """重複応募チェック"""
        form = ApplicationForm(
            data={
                'candidate': candidate.pk,
                'job': job.pk,
                'status': ApplicationStatusChoices.NEW,
            },
            tenant=tenant
        )
        # 既存応募があるため無効
        assert not form.is_valid()
        assert 'この候補者は既にこの求人に応募しています' in str(form.errors)

    @pytest.mark.django_db
    def test_form_clean_no_duplicate(self, tenant, candidate, admin_user):
        """重複なしの場合は有効"""
        job2 = Job.objects.create(
            tenant=tenant,
            title='別の求人',
            unique_code='JOB-FORM-003',
            status=JobStatusChoices.ACTIVE,
            created_by=admin_user,
        )
        form = ApplicationForm(
            data={
                'candidate': candidate.pk,
                'job': job2.pk,
                'status': ApplicationStatusChoices.NEW,
            },
            tenant=tenant
        )
        assert form.is_valid()


# =============================================================================
# ApplicationFilterForm Tests
# =============================================================================

class TestApplicationFilterFormComprehensive:
    """ApplicationFilterForm包括テスト"""

    @pytest.mark.django_db
    def test_filter_form_init_with_tenant(self, tenant, job):
        """テナント付きフィルタフォーム初期化"""
        form = ApplicationFilterForm(tenant=tenant)
        assert job in form.fields['job'].queryset

    @pytest.mark.django_db
    def test_filter_form_without_tenant(self):
        """テナントなしフィルタフォーム"""
        form = ApplicationFilterForm()
        assert form.fields['job'].queryset is None


# =============================================================================
# ApplicationStatusForm Tests
# =============================================================================

class TestApplicationStatusFormComprehensive:
    """ApplicationStatusForm包括テスト"""

    @pytest.mark.django_db
    def test_status_form_valid(self):
        """有効なステータスフォーム"""
        form = ApplicationStatusForm(data={
            'status': ApplicationStatusChoices.DOCUMENT_SCREENING,
            'notes': 'テストノート',
        })
        assert form.is_valid()

    @pytest.mark.django_db
    def test_status_form_notes_optional(self):
        """notesはオプション"""
        form = ApplicationStatusForm(data={
            'status': ApplicationStatusChoices.NEW,
        })
        assert form.is_valid()


# =============================================================================
# UnifiedApplicationForm Tests
# =============================================================================

class TestUnifiedApplicationFormComprehensive:
    """UnifiedApplicationForm包括テスト"""

    @pytest.mark.django_db
    def test_form_init_with_tenant(self, tenant, open_job, application_source, admin_user):
        """テナント付きフォーム初期化"""
        form = UnifiedApplicationForm(tenant=tenant, user=admin_user)
        assert form.tenant == tenant
        assert form.user == admin_user

    @pytest.mark.django_db
    def test_clean_email_existing_candidate(self, tenant, candidate, open_job, admin_user):
        """既存候補者のメールチェック"""
        form = UnifiedApplicationForm(
            data={
                'name': 'テスト名',
                'email': candidate.email,  # 既存候補者のメール
                'job': open_job.pk,
            },
            tenant=tenant,
            user=admin_user,
        )
        form.full_clean()
        assert form._existing_candidate == candidate

    @pytest.mark.django_db
    def test_clean_email_new_candidate(self, tenant, open_job, admin_user):
        """新規候補者のメールチェック"""
        form = UnifiedApplicationForm(
            data={
                'name': '新規候補者',
                'email': 'new@test.com',
                'job': open_job.pk,
            },
            tenant=tenant,
            user=admin_user,
        )
        form.full_clean()
        assert form._existing_candidate is None

    @pytest.mark.django_db
    def test_clean_duplicate_application(self, tenant, candidate, open_job, application, admin_user):
        """重複応募チェック"""
        # 既存応募を作成
        form = UnifiedApplicationForm(
            data={
                'name': candidate.name,
                'email': candidate.email,
                'job': application.job.pk,  # 既に応募済みの求人
            },
            tenant=tenant,
            user=admin_user,
        )
        assert not form.is_valid()

    @pytest.mark.django_db
    def test_save_new_candidate(self, tenant, open_job, admin_user):
        """新規候補者と応募を保存（フォームバリデーション）"""
        form = UnifiedApplicationForm(
            data={
                'name': '新規太郎',
                'name_kana': 'シンキタロウ',
                'email': 'shinki@test.com',
                'phone': '09012345678',  # ハイフンなし形式
                'gender': GenderChoices.MALE,
                'employment_status': EmploymentStatusChoices.EMPLOYED,
                'job': open_job.pk,
                'skills': 'Python, JavaScript',
                'qualifications': '基本情報, TOEIC800',
                'notes': 'テストノート',
            },
            tenant=tenant,
            user=admin_user,
        )
        # フォームバリデーションが通ることを確認
        assert form.is_valid(), form.errors
        # 新規候補者フラグを確認
        assert form._existing_candidate is None

    @pytest.mark.django_db
    def test_save_existing_candidate(self, tenant, candidate, admin_user):
        """既存候補者への応募（フォームバリデーション）"""
        new_job = Job.objects.create(
            tenant=tenant,
            title='新規求人',
            unique_code='JOB-UNIFIED-001',
            status=JobStatusChoices.ACTIVE,
            created_by=admin_user,
        )

        form = UnifiedApplicationForm(
            data={
                'name': candidate.name,
                'email': candidate.email,
                'job': new_job.pk,
            },
            tenant=tenant,
            user=admin_user,
        )
        assert form.is_valid(), form.errors
        # 既存候補者が検出されることを確認
        assert form._existing_candidate == candidate

    @pytest.mark.django_db
    def test_save_with_agent_user(self, tenant, open_job, agent_user, agent_company):
        """エージェントユーザーによるフォームバリデーション"""
        # プロファイルにエージェント会社を設定
        Profile.objects.create(
            user=agent_user,
            tenant=tenant,
            agent_company=agent_company,
        )

        form = UnifiedApplicationForm(
            data={
                'name': 'エージェント候補者',
                'email': 'agent-candidate@test.com',
                'job': open_job.pk,
            },
            tenant=tenant,
            user=agent_user,
        )
        # フォームバリデーションが通ることを確認
        assert form.is_valid(), form.errors
        # ユーザーがエージェントであることを確認
        assert form.user == agent_user

    @pytest.mark.django_db
    def test_skills_field_validation(self, tenant, open_job, admin_user):
        """スキルフィールドのバリデーション"""
        form = UnifiedApplicationForm(
            data={
                'name': 'スキル候補者',
                'email': 'skills@test.com',
                'job': open_job.pk,
                'skills': 'Python, JavaScript, AWS,  React  ',
                'qualifications': '',
            },
            tenant=tenant,
            user=admin_user,
        )
        # フォームバリデーションが通ることを確認
        assert form.is_valid(), form.errors
        # cleaned_dataにスキルが含まれることを確認
        assert 'skills' in form.cleaned_data
        assert 'Python' in form.cleaned_data['skills']

    @pytest.mark.django_db
    def test_existing_candidate_property(self, tenant, candidate, open_job, admin_user):
        """existing_candidateプロパティ"""
        form = UnifiedApplicationForm(
            data={
                'name': candidate.name,
                'email': candidate.email,
                'job': open_job.pk,
            },
            tenant=tenant,
            user=admin_user,
        )
        form.full_clean()

        assert form.existing_candidate == candidate

    @pytest.mark.django_db
    def test_form_without_optional_fields(self, tenant, open_job, admin_user):
        """オプションフィールドなしでバリデーション"""
        form = UnifiedApplicationForm(
            data={
                'name': '最小情報',
                'email': 'minimal@test.com',
                'job': open_job.pk,
            },
            tenant=tenant,
            user=admin_user,
        )
        # 必須項目のみでバリデーションが通ることを確認
        assert form.is_valid(), form.errors
        # 新規候補者として認識されることを確認
        assert form._existing_candidate is None
