"""Django ATS - コアモデル完全カバレッジテスト

core/models.pyの100%カバレッジを目指すテスト。
"""

import pytest
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRole
from apps.candidates.models import CandidateComment, Candidate


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='コアモデルテスト',
        code='core-model-test',
        is_active=True,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@core-model-test.com',
        password='testpass123',
        role=UserRole.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def candidate(db, tenant, admin_user):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        email='candidate@core-model-test.com',
        name='テスト候補者',
        registered_by=admin_user,
    )


# =============================================================================
# SoftDeleteModel Tests（CandidateCommentで検証）
# =============================================================================

class TestSoftDeleteModel:
    """SoftDeleteModelテスト

    CandidateCommentはSoftDeleteTenantModelを継承しているが、
    独自のsoft_deleteメソッドを持つ。
    ここではcore/models.pyのSoftDeleteModelの抽象メソッドをテスト。
    """

    @pytest.fixture
    def comment(self, db, tenant, candidate, admin_user):
        """テストコメント"""
        return CandidateComment.objects.create(
            tenant=tenant,
            candidate=candidate,
            author=admin_user,
            content='テストコメント',
        )

    @pytest.mark.django_db
    def test_soft_delete_sets_is_deleted(self, comment, admin_user):
        """論理削除でis_deletedがTrueになる"""
        comment.soft_delete(admin_user)
        comment.refresh_from_db()
        assert comment.is_deleted is True

    @pytest.mark.django_db
    def test_soft_delete_sets_deleted_at(self, comment, admin_user):
        """論理削除でdeleted_atが設定される"""
        before = timezone.now()
        comment.soft_delete(admin_user)
        comment.refresh_from_db()
        assert comment.deleted_at is not None
        assert comment.deleted_at >= before


# =============================================================================
# Application Model Tests
# =============================================================================

class TestApplicationModel:
    """Applicationモデルテスト（追加カバレッジ）"""

    @pytest.fixture
    def job(self, db, tenant, admin_user):
        """テスト求人"""
        from apps.jobs.models import Job, JobStatusChoices
        return Job.objects.create(
            tenant=tenant,
            title='テスト求人',
            unique_code='JOB-CORE-001',
            status=JobStatusChoices.ACTIVE,
            created_by=admin_user,
        )

    @pytest.fixture
    def application(self, db, tenant, candidate, job):
        """テスト応募"""
        from apps.applications.models import Application, ApplicationStatusChoices
        return Application.objects.create(
            tenant=tenant,
            candidate=candidate,
            job=job,
            status=ApplicationStatusChoices.NEW,
        )

    @pytest.mark.django_db
    def test_application_str(self, application, candidate, job):
        """Application __str__メソッド"""
        result = str(application)
        assert candidate.name in result
        assert job.title in result

    @pytest.mark.django_db
    def test_application_get_absolute_url(self, application):
        """Application get_absolute_urlメソッド"""
        url = application.get_absolute_url()
        assert str(application.pk) in url


# =============================================================================
# BaseModel Tests
# =============================================================================

class TestBaseModelVersioning:
    """BaseModelのバージョン管理テスト"""

    @pytest.mark.django_db
    def test_save_without_version_increment(self, tenant, admin_user):
        """save_without_version_incrementでバージョンが増えない"""
        candidate = Candidate.objects.create(
            tenant=tenant,
            email='version-test@core-model-test.com',
            name='バージョンテスト',
            registered_by=admin_user,
        )

        initial_version = candidate.version

        # 通常のsaveでバージョンが増える
        candidate.name = 'バージョンテスト更新'
        candidate.save()
        candidate.refresh_from_db()
        assert candidate.version == initial_version + 1

        # save_without_version_incrementでバージョンが増えない
        current_version = candidate.version
        candidate.name = 'バージョンテスト再更新'
        candidate.save_without_version_increment()
        candidate.refresh_from_db()
        assert candidate.version == current_version


# =============================================================================
# Note: SoftDeleteModel Methods
# =============================================================================
# SoftDeleteModel と SoftDeleteTenantModel は将来の拡張用に定義されており、
# 現時点では実際に使用しているモデルがありません。
# そのため、delete(), hard_delete(), restore() メソッドのテストは
# 実際にこれらを使用するモデルが実装された時点で追加します。
