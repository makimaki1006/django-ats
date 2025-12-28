"""Django ATS - 応募フォーム完全カバレッジテスト

applications/forms.pyの100%カバレッジを目指すテスト。
"""

import pytest
from django.test import RequestFactory

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRole, Profile
from apps.candidates.models import Candidate, GenderChoices, EmploymentStatusChoices
from apps.jobs.models import Job, JobStatusChoices
from apps.applications.models import Application, ApplicationStatusHistory
from apps.applications.forms import UnifiedApplicationForm
from apps.settings_app.models import ApplicationSource


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
    user = CustomUser.objects.create_user(
        email='admin@application-form-test.com',
        password='testpass123',
        role=UserRole.CLIENT_ADMIN,
        tenant=tenant,
    )
    # プロファイル作成
    Profile.objects.get_or_create(tenant=tenant, user=user)
    return user


@pytest.fixture
def active_job(db, tenant, admin_user):
    """アクティブな求人"""
    return Job.objects.create(
        tenant=tenant,
        title='テストエンジニア',
        unique_code='JOB-FORM-001',
        status=JobStatusChoices.ACTIVE,
        created_by=admin_user,
    )


@pytest.fixture
def application_source(db, tenant):
    """応募経路"""
    return ApplicationSource.objects.create(
        tenant=tenant,
        name='直接応募',
        is_active=True,
    )


# =============================================================================
# UnifiedApplicationForm Tests
# =============================================================================

class TestUnifiedApplicationFormSave:
    """UnifiedApplicationForm.saveメソッドテスト"""

    @pytest.mark.django_db
    def test_save_creates_new_candidate_and_application(
        self, tenant, admin_user, active_job, application_source
    ):
        """新規候補者と応募を作成"""
        form_data = {
            'name': '新規テスト太郎',
            'name_kana': 'シンキテストタロウ',
            'email': 'new-candidate@form-test.com',
            'phone': '09012345678',  # 数字のみの形式
            'gender': GenderChoices.MALE,
            'current_company': '株式会社テスト',
            'current_position': 'エンジニア',
            'employment_status': EmploymentStatusChoices.EMPLOYED,
            'years_of_experience': 5,
            'desired_salary': 600,
            'skills': 'Python, Django, AWS',
            'qualifications': '基本情報技術者, AWS SAA',
            'education': '〇〇大学 工学部',
            'resume_url': 'https://example.com/resume.pdf',
            'cv_url': 'https://example.com/cv.pdf',
            'job': active_job.pk,
            'source': application_source.pk,
            'notes': 'フォームからの応募',
        }

        form = UnifiedApplicationForm(
            data=form_data,
            tenant=tenant,
            user=admin_user
        )

        assert form.is_valid(), form.errors

        candidate, application, is_new_candidate = form.save()

        # 新規候補者が作成されたことを確認
        assert is_new_candidate is True
        assert candidate.name == '新規テスト太郎'
        assert candidate.email == 'new-candidate@form-test.com'
        assert candidate.skills == ['Python', 'Django', 'AWS']
        assert candidate.qualifications == ['基本情報技術者', 'AWS SAA']
        assert candidate.tenant == tenant
        assert candidate.registered_by == admin_user

        # 応募が作成されたことを確認
        assert application.candidate == candidate
        assert application.job == active_job
        assert application.source == application_source
        assert application.tenant == tenant

        # ステータス履歴が作成されたことを確認
        history = ApplicationStatusHistory.objects.filter(application=application).first()
        assert history is not None
        assert '統合応募フォームから登録' in history.notes

    @pytest.mark.django_db
    def test_save_with_existing_candidate(
        self, tenant, admin_user, active_job, application_source
    ):
        """既存候補者への応募"""
        # 既存候補者を作成
        existing_candidate = Candidate.objects.create(
            tenant=tenant,
            email='existing@form-test.com',
            name='既存候補者',
            registered_by=admin_user,
        )

        form_data = {
            'name': '既存候補者',
            'email': 'existing@form-test.com',
            'job': active_job.pk,
            'source': application_source.pk,
        }

        form = UnifiedApplicationForm(
            data=form_data,
            tenant=tenant,
            user=admin_user
        )

        assert form.is_valid(), form.errors

        candidate, application, is_new_candidate = form.save()

        # 既存候補者が使用されたことを確認
        assert is_new_candidate is False
        assert candidate.pk == existing_candidate.pk
        assert application.candidate == existing_candidate

    @pytest.mark.django_db
    def test_save_with_empty_skills_and_qualifications(
        self, tenant, admin_user, active_job
    ):
        """スキル・資格が空の場合"""
        form_data = {
            'name': '最小限太郎',
            'email': 'minimal@form-test.com',
            'job': active_job.pk,
            'skills': '',
            'qualifications': '',
        }

        form = UnifiedApplicationForm(
            data=form_data,
            tenant=tenant,
            user=admin_user
        )

        assert form.is_valid(), form.errors

        candidate, application, is_new_candidate = form.save()

        assert candidate.skills == []
        assert candidate.qualifications == []

    @pytest.mark.django_db
    def test_save_with_default_gender_and_employment_status(
        self, tenant, admin_user, active_job
    ):
        """性別・就業状況がデフォルトの場合"""
        form_data = {
            'name': 'デフォルト太郎',
            'email': 'default@form-test.com',
            'job': active_job.pk,
            'gender': '',
            'employment_status': '',
        }

        form = UnifiedApplicationForm(
            data=form_data,
            tenant=tenant,
            user=admin_user
        )

        assert form.is_valid(), form.errors

        candidate, application, is_new_candidate = form.save()

        # デフォルト値が設定される
        assert candidate.gender == GenderChoices.UNSPECIFIED
        assert candidate.employment_status == EmploymentStatusChoices.EMPLOYED

    @pytest.mark.django_db
    def test_clean_detects_duplicate_application(
        self, tenant, admin_user, active_job
    ):
        """既存候補者の重複応募を検出"""
        # 既存候補者と応募を作成
        existing_candidate = Candidate.objects.create(
            tenant=tenant,
            email='duplicate@form-test.com',
            name='重複候補者',
            registered_by=admin_user,
        )
        Application.objects.create(
            tenant=tenant,
            candidate=existing_candidate,
            job=active_job,
        )

        form_data = {
            'name': '重複候補者',
            'email': 'duplicate@form-test.com',
            'job': active_job.pk,
        }

        form = UnifiedApplicationForm(
            data=form_data,
            tenant=tenant,
            user=admin_user
        )

        assert form.is_valid() is False
        assert '既にこの求人に応募しています' in str(form.errors)

    @pytest.mark.django_db
    def test_existing_candidate_property(self, tenant, admin_user, active_job):
        """existing_candidateプロパティ"""
        # 既存候補者を作成
        existing_candidate = Candidate.objects.create(
            tenant=tenant,
            email='property-test@form-test.com',
            name='プロパティテスト',
            registered_by=admin_user,
        )

        form_data = {
            'name': 'プロパティテスト',
            'email': 'property-test@form-test.com',
            'job': active_job.pk,
        }

        form = UnifiedApplicationForm(
            data=form_data,
            tenant=tenant,
            user=admin_user
        )

        form.is_valid()

        assert form.existing_candidate == existing_candidate
