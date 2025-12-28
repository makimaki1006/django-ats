"""
Django ATS - ビュー統合テスト
CRUD機能の統合テスト
"""

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser, UserRoleChoices
from apps.tenants.models import Tenant
from apps.candidates.models import Candidate
from apps.jobs.models import Job, JobStatusChoices, EmploymentTypeChoices
from apps.applications.models import Application, ApplicationStatusChoices
from apps.interviews.models import Interview, InterviewTypeChoices, InterviewStatusChoices


@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='テストテナント',
        code='test-tenant',
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """テストユーザー"""
    user = CustomUser.objects.create_user(
        email='test@example.com',
        password='testpass123',
        first_name='テスト',
        last_name='ユーザー',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )
    return user


@pytest.fixture
def client_logged_in(client, user):
    """ログイン済みクライアント"""
    client.login(email='test@example.com', password='testpass123')
    return client


@pytest.fixture
def candidate(db, tenant, user):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        name='田中太郎',
        email='tanaka@example.com',
        phone='+819012345678',
        registered_by=user,
    )


@pytest.fixture
def job(db, tenant, user):
    """テスト求人"""
    return Job.objects.create(
        tenant=tenant,
        title='ソフトウェアエンジニア',
        unique_code='JOB-001',
        status=JobStatusChoices.ACTIVE,
        employment_type=EmploymentTypeChoices.FULL_TIME,
        description='エンジニア募集',
        created_by=user,
    )


@pytest.fixture
def application(db, tenant, candidate, job, user):
    """テスト応募"""
    return Application.objects.create(
        tenant=tenant,
        candidate=candidate,
        job=job,
        status=ApplicationStatusChoices.NEW,
        registered_by=user,
    )


@pytest.fixture
def interview(db, tenant, application, user):
    """テスト面接"""
    return Interview.objects.create(
        tenant=tenant,
        application=application,
        interview_type=InterviewTypeChoices.VIDEO,
        interview_round=1,
        scheduled_at=timezone.now() + timezone.timedelta(days=1),
        duration_minutes=60,
        interviewer=user,
    )


class TestCandidateViews:
    """候補者ビューのテスト"""

    def test_candidate_list_requires_login(self, client):
        """候補者一覧はログイン必須"""
        response = client.get(reverse('candidates:candidate_list'))
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    @pytest.mark.django_db
    def test_candidate_list_status_code(self, client_logged_in):
        """候補者一覧のステータスコード"""
        response = client_logged_in.get(reverse('candidates:candidate_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_candidate_detail_status_code(self, client_logged_in, candidate):
        """候補者詳細のステータスコード"""
        response = client_logged_in.get(
            reverse('candidates:candidate_detail', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_candidate_create_form_status_code(self, client_logged_in):
        """候補者作成フォームのステータスコード"""
        response = client_logged_in.get(reverse('candidates:candidate_create'))
        assert response.status_code == 200


class TestJobViews:
    """求人ビューのテスト"""

    def test_job_list_requires_login(self, client):
        """求人一覧はログイン必須"""
        response = client.get(reverse('jobs:job_list'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_job_list_status_code(self, client_logged_in):
        """求人一覧のステータスコード"""
        response = client_logged_in.get(reverse('jobs:job_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_job_detail_status_code(self, client_logged_in, job):
        """求人詳細のステータスコード"""
        response = client_logged_in.get(
            reverse('jobs:job_detail', kwargs={'pk': job.pk})
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_job_duplicate(self, client_logged_in, job):
        """求人複製"""
        response = client_logged_in.post(
            reverse('jobs:job_duplicate', kwargs={'pk': job.pk})
        )
        assert response.status_code == 302
        assert Job.objects.filter(unique_code__startswith='JOB-001_copy').exists()


class TestApplicationViews:
    """応募ビューのテスト"""

    def test_application_list_requires_login(self, client):
        """応募一覧はログイン必須"""
        response = client.get(reverse('applications:application_list'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_application_list_status_code(self, client_logged_in):
        """応募一覧のステータスコード"""
        response = client_logged_in.get(reverse('applications:application_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_application_detail_status_code(self, client_logged_in, application):
        """応募詳細のステータスコード"""
        response = client_logged_in.get(
            reverse('applications:application_detail', kwargs={'pk': application.pk})
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_application_kanban_status_code(self, client_logged_in):
        """応募カンバンのステータスコード"""
        response = client_logged_in.get(reverse('applications:application_kanban'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_application_status_change(self, client_logged_in, application):
        """応募ステータス変更"""
        response = client_logged_in.post(
            reverse('applications:application_status', kwargs={'pk': application.pk}),
            {
                'status': ApplicationStatusChoices.DOCUMENT_SCREENING,
                'notes': 'テスト',
            }
        )
        assert response.status_code == 302
        application.refresh_from_db()
        assert application.status == ApplicationStatusChoices.DOCUMENT_SCREENING


class TestInterviewViews:
    """面接ビューのテスト"""

    def test_interview_list_requires_login(self, client):
        """面接一覧はログイン必須"""
        response = client.get(reverse('interviews:interview_list'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_interview_list_status_code(self, client_logged_in):
        """面接一覧のステータスコード"""
        response = client_logged_in.get(reverse('interviews:interview_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_interview_detail_status_code(self, client_logged_in, interview):
        """面接詳細のステータスコード"""
        response = client_logged_in.get(
            reverse('interviews:interview_detail', kwargs={'pk': interview.pk})
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_interview_calendar_status_code(self, client_logged_in):
        """面接カレンダーのステータスコード"""
        response = client_logged_in.get(reverse('interviews:interview_calendar'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_interview_cancel(self, client_logged_in, interview):
        """面接キャンセル"""
        response = client_logged_in.post(
            reverse('interviews:interview_cancel', kwargs={'pk': interview.pk}),
            {'reason': 'テストキャンセル'}
        )
        assert response.status_code == 302
        interview.refresh_from_db()
        assert interview.status == InterviewStatusChoices.CANCELLED


class TestDashboardViews:
    """ダッシュボードビューのテスト"""

    def test_dashboard_requires_login(self, client):
        """ダッシュボードはログイン必須"""
        response = client.get(reverse('dashboard'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_dashboard_status_code(self, client_logged_in):
        """ダッシュボードのステータスコード"""
        response = client_logged_in.get(reverse('dashboard'))
        assert response.status_code == 200


class TestTenantIsolation:
    """テナント分離のテスト"""

    @pytest.mark.django_db
    def test_cannot_access_other_tenant_candidate(self, client_logged_in, db, user):
        """他テナントの候補者にアクセスできない"""
        other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        other_user = CustomUser.objects.create_user(
            email='other@example.com',
            password='testpass123',
            tenant=other_tenant,
        )
        other_candidate = Candidate.objects.create(
            tenant=other_tenant,
            name='他テナント候補者',
            email='other-candidate@example.com',
            registered_by=other_user,
        )

        response = client_logged_in.get(
            reverse('candidates:candidate_detail', kwargs={'pk': other_candidate.pk})
        )
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_cannot_access_other_tenant_job(self, client_logged_in, db, user):
        """他テナントの求人にアクセスできない"""
        other_tenant = Tenant.objects.create(
            name='他テナント2',
            code='other-tenant-2',
            is_active=True,
        )
        other_user = CustomUser.objects.create_user(
            email='other2@example.com',
            password='testpass123',
            tenant=other_tenant,
        )
        other_job = Job.objects.create(
            tenant=other_tenant,
            title='他テナント求人',
            unique_code='OTHER-001',
            status=JobStatusChoices.ACTIVE,
            employment_type=EmploymentTypeChoices.FULL_TIME,
            description='説明',
            created_by=other_user,
        )

        response = client_logged_in.get(
            reverse('jobs:job_detail', kwargs={'pk': other_job.pk})
        )
        assert response.status_code == 404


class TestInterviewSupportViews:
    """面接サポートビューのテスト"""

    def test_interview_support_dashboard_requires_login(self, client):
        """面接サポートダッシュボードはログイン必須"""
        response = client.get(reverse('interviews:interview_support_dashboard'))
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    @pytest.mark.django_db
    def test_interview_support_dashboard_status_code(self, client_logged_in):
        """面接サポートダッシュボードのステータスコード"""
        response = client_logged_in.get(reverse('interviews:interview_support_dashboard'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_interview_support_detail_requires_login(self, client, interview):
        """面接サポート詳細はログイン必須"""
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': interview.pk})
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_interview_support_detail_only_for_interviewer(self, client_logged_in, interview, user):
        """面接サポート詳細は担当面接官のみアクセス可能"""
        # interviewのinterviewerはuserなのでアクセス可能
        response = client_logged_in.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': interview.pk})
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_interview_support_detail_not_accessible_for_non_interviewer(
        self, client, tenant, interview, db
    ):
        """面接サポート詳細は担当外ユーザーはアクセス不可"""
        other_user = CustomUser.objects.create_user(
            email='other-interviewer@example.com',
            password='testpass123',
            first_name='他の',
            last_name='ユーザー',
            role=UserRoleChoices.INTERVIEWER,
            tenant=tenant,
        )
        client.login(email='other-interviewer@example.com', password='testpass123')
        response = client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': interview.pk})
        )
        # 担当外なので404
        assert response.status_code == 404


class TestCSVImportViews:
    """CSVインポートビューのテスト"""

    def test_csv_import_requires_login(self, client):
        """CSVインポートはログイン必須"""
        response = client.get(reverse('candidates:csv_import'))
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    @pytest.mark.django_db
    def test_csv_import_status_code(self, client_logged_in):
        """CSVインポートのステータスコード"""
        response = client_logged_in.get(reverse('candidates:csv_import'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_csv_import_history_status_code(self, client_logged_in):
        """CSVインポート履歴のステータスコード"""
        response = client_logged_in.get(reverse('candidates:csv_import_history'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_csv_template_download(self, client_logged_in):
        """CSVテンプレートダウンロード"""
        response = client_logged_in.get(reverse('candidates:csv_template_download'))
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv; charset=utf-8-sig'
        assert 'attachment' in response['Content-Disposition']


class TestCommentViews:
    """コメントビューのテスト"""

    @pytest.mark.django_db
    def test_comment_create_requires_login(self, client, candidate):
        """コメント作成はログイン必須"""
        response = client.post(
            reverse('candidates:comment_create', kwargs={'candidate_pk': candidate.pk}),
            {'content': 'テストコメント'}
        )
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    @pytest.mark.django_db
    def test_comment_create_success(self, client_logged_in, candidate):
        """コメント作成成功"""
        from apps.candidates.models import CandidateComment
        initial_count = CandidateComment.objects.count()
        response = client_logged_in.post(
            reverse('candidates:comment_create', kwargs={'candidate_pk': candidate.pk}),
            {'content': 'テストコメント'}
        )
        assert response.status_code == 302
        assert CandidateComment.objects.count() == initial_count + 1

    @pytest.mark.django_db
    def test_comment_create_empty_content(self, client_logged_in, candidate):
        """空のコメントは作成できない"""
        from apps.candidates.models import CandidateComment
        initial_count = CandidateComment.objects.count()
        response = client_logged_in.post(
            reverse('candidates:comment_create', kwargs={'candidate_pk': candidate.pk}),
            {'content': ''}
        )
        # フォームエラーでリダイレクト
        assert response.status_code == 302
        assert CandidateComment.objects.count() == initial_count


class TestRoleBasedAccess:
    """ロールベースアクセス制御のテスト"""

    @pytest.mark.django_db
    def test_interviewer_cannot_access_csv_import(self, client, tenant, db):
        """面接官はCSVインポートにアクセスできない"""
        interviewer = CustomUser.objects.create_user(
            email='interviewer@example.com',
            password='testpass123',
            role=UserRoleChoices.INTERVIEWER,
            tenant=tenant,
        )
        client.login(email='interviewer@example.com', password='testpass123')
        response = client.get(reverse('candidates:csv_import'))
        # 権限不足で403または302
        assert response.status_code in [302, 403]

    @pytest.mark.django_db
    def test_agent_cannot_create_candidate(self, client, tenant, db):
        """エージェントは候補者を作成できない"""
        agent = CustomUser.objects.create_user(
            email='agent@example.com',
            password='testpass123',
            role=UserRoleChoices.AGENT,
            tenant=tenant,
        )
        client.login(email='agent@example.com', password='testpass123')
        response = client.get(reverse('candidates:candidate_create'))
        # 権限不足で403または302
        assert response.status_code in [302, 403]

    @pytest.mark.django_db
    def test_consultant_can_access_csv_import(self, client, tenant, db):
        """コンサルタントはCSVインポートにアクセスできる"""
        consultant = CustomUser.objects.create_user(
            email='consultant@example.com',
            password='testpass123',
            role=UserRoleChoices.CONSULTANT,
            tenant=tenant,
        )
        client.login(email='consultant@example.com', password='testpass123')
        response = client.get(reverse('candidates:csv_import'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_hiring_manager_can_create_candidate(self, client, tenant, db):
        """採用責任者は候補者を作成できる"""
        hiring_manager = CustomUser.objects.create_user(
            email='hiring-manager@example.com',
            password='testpass123',
            role=UserRoleChoices.HIRING_MANAGER,
            tenant=tenant,
        )
        client.login(email='hiring-manager@example.com', password='testpass123')
        response = client.get(reverse('candidates:candidate_create'))
        assert response.status_code == 200
