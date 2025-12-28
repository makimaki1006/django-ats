"""Django ATS - アカウントモデル完全カバレッジテスト

accounts/models.pyの100%カバレッジを目指すテスト。
"""

import pytest

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRole, Profile
from apps.agents.models import AgentCompany


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='アカウントモデルテスト',
        code='account-model-test',
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
def system_admin(db, tenant):
    """システム管理者"""
    return CustomUser.objects.create_user(
        email='sysadmin@account-model-test.com',
        password='testpass123',
        role=UserRole.SYSTEM_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def consultant(db, tenant):
    """採用コンサルタント"""
    return CustomUser.objects.create_user(
        email='consultant@account-model-test.com',
        password='testpass123',
        role=UserRole.CONSULTANT,
        tenant=tenant,
    )


@pytest.fixture
def hiring_manager(db, tenant):
    """採用責任者"""
    return CustomUser.objects.create_user(
        email='hiring@account-model-test.com',
        password='testpass123',
        role=UserRole.HIRING_MANAGER,
        tenant=tenant,
    )


@pytest.fixture
def interviewer(db, tenant):
    """面接官"""
    return CustomUser.objects.create_user(
        email='interviewer@account-model-test.com',
        password='testpass123',
        role=UserRole.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def agent_user(db, tenant):
    """エージェントユーザー"""
    return CustomUser.objects.create_user(
        email='agent@account-model-test.com',
        password='testpass123',
        role=UserRole.AGENT,
        tenant=tenant,
    )


# =============================================================================
# CustomUserManager Tests
# =============================================================================

class TestCustomUserManager:
    """CustomUserManagerテスト"""

    @pytest.mark.django_db
    def test_create_superuser_with_is_staff_false(self, tenant):
        """スーパーユーザー作成時is_staff=Falseでエラー"""
        with pytest.raises(ValueError) as exc_info:
            CustomUser.objects.create_superuser(
                email='super@test.com',
                password='testpass123',
                tenant=tenant,
                is_staff=False,
            )
        assert 'is_staff=True' in str(exc_info.value)

    @pytest.mark.django_db
    def test_create_superuser_with_is_superuser_false(self, tenant):
        """スーパーユーザー作成時is_superuser=Falseでエラー"""
        with pytest.raises(ValueError) as exc_info:
            CustomUser.objects.create_superuser(
                email='super@test.com',
                password='testpass123',
                tenant=tenant,
                is_superuser=False,
            )
        assert 'is_superuser=True' in str(exc_info.value)


# =============================================================================
# CustomUser Role Property Tests
# =============================================================================

class TestCustomUserRoleProperties:
    """CustomUserロールプロパティテスト"""

    @pytest.mark.django_db
    def test_is_consultant_true(self, consultant):
        """is_consultant（採用コンサルタント）"""
        assert consultant.is_consultant is True

    @pytest.mark.django_db
    def test_is_consultant_false(self, interviewer):
        """is_consultant（面接官は該当しない）"""
        assert interviewer.is_consultant is False

    @pytest.mark.django_db
    def test_is_hiring_manager_true(self, hiring_manager):
        """is_hiring_manager（採用責任者）"""
        assert hiring_manager.is_hiring_manager is True

    @pytest.mark.django_db
    def test_is_hiring_manager_false(self, consultant):
        """is_hiring_manager（コンサルタントは該当しない）"""
        assert consultant.is_hiring_manager is False


# =============================================================================
# CustomUser can_access_tenant Tests
# =============================================================================

class TestCustomUserCanAccessTenant:
    """can_access_tenantメソッドテスト"""

    @pytest.mark.django_db
    def test_system_admin_can_access_any_tenant(self, system_admin, other_tenant):
        """システム管理者は全テナントにアクセス可能"""
        assert system_admin.can_access_tenant(other_tenant) is True

    @pytest.mark.django_db
    def test_regular_user_can_access_own_tenant(self, consultant, tenant):
        """一般ユーザーは自テナントにアクセス可能"""
        assert consultant.can_access_tenant(tenant) is True

    @pytest.mark.django_db
    def test_regular_user_cannot_access_other_tenant(self, consultant, other_tenant):
        """一般ユーザーは他テナントにアクセス不可"""
        assert consultant.can_access_tenant(other_tenant) is False

    @pytest.mark.django_db
    def test_can_access_tenant_with_none(self, consultant):
        """テナントがNoneの場合はFalse"""
        assert consultant.can_access_tenant(None) is False


# =============================================================================
# Profile Notification Settings Tests
# =============================================================================

class TestProfileNotificationSettings:
    """Profileの通知設定テスト"""

    @pytest.fixture
    def profile(self, db, tenant, consultant):
        """プロファイル"""
        return Profile.objects.create(
            tenant=tenant,
            user=consultant,
            notification_settings={},
        )

    @pytest.mark.django_db
    def test_get_notification_setting_default(self, profile):
        """通知設定取得（デフォルト値）"""
        result = profile.get_notification_setting('email_new_application')
        assert result is True  # デフォルトはTrue

    @pytest.mark.django_db
    def test_get_notification_setting_custom_default(self, profile):
        """通知設定取得（カスタムデフォルト値）"""
        result = profile.get_notification_setting('unknown_setting', default=False)
        assert result is False

    @pytest.mark.django_db
    def test_get_notification_setting_existing(self, profile):
        """通知設定取得（既存設定）"""
        profile.notification_settings['email_interview'] = False
        profile.save()
        result = profile.get_notification_setting('email_interview')
        assert result is False

    @pytest.mark.django_db
    def test_set_notification_setting(self, profile):
        """通知設定保存"""
        profile.set_notification_setting('email_new_application', False)
        profile.refresh_from_db()
        assert profile.notification_settings['email_new_application'] is False

    @pytest.mark.django_db
    def test_set_notification_setting_new_key(self, profile):
        """通知設定保存（新規キー）"""
        profile.set_notification_setting('custom_notification', True)
        profile.refresh_from_db()
        assert profile.notification_settings['custom_notification'] is True
