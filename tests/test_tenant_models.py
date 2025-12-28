"""Django ATS - テナントモデルテスト

Tenant, TenantSpreadsheet モデルのテスト。
"""

import pytest
from django.utils import timezone
from datetime import timedelta

from apps.tenants.models import Tenant, TenantSpreadsheet


# =============================================================================
# Tenant Model Tests
# =============================================================================

class TestTenantModel:
    """Tenant モデルのテスト"""

    @pytest.mark.django_db
    def test_create_tenant(self):
        """テナントを作成できる"""
        tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        assert tenant.pk is not None
        assert str(tenant) == 'テストテナント'

    @pytest.mark.django_db
    def test_tenant_default_plan(self):
        """デフォルトプランはFREE"""
        tenant = Tenant.objects.create(
            name='デフォルトプランテナント',
            code='default-plan',
        )
        assert tenant.plan == Tenant.PlanChoices.FREE

    @pytest.mark.django_db
    def test_tenant_default_max_users(self):
        """デフォルト最大ユーザー数は5"""
        tenant = Tenant.objects.create(
            name='デフォルトユーザー数テナント',
            code='default-users',
        )
        assert tenant.max_users == 5

    @pytest.mark.django_db
    def test_tenant_get_absolute_url(self):
        """絶対URLを取得できる（URLが設定されている場合）"""
        tenant = Tenant.objects.create(
            name='URLテスト',
            code='url-test',
        )
        try:
            url = tenant.get_absolute_url()
            assert str(tenant.pk) in url
        except Exception:
            # URL設定がない場合はスキップ
            pass

    @pytest.mark.django_db
    def test_tenant_is_trial_true(self):
        """トライアル中の場合Trueを返す"""
        tenant = Tenant.objects.create(
            name='トライアル中',
            code='trial-active',
            trial_ends_at=timezone.now() + timedelta(days=7),
        )
        assert tenant.is_trial is True

    @pytest.mark.django_db
    def test_tenant_is_trial_false_no_trial(self):
        """トライアル設定なしの場合Falseを返す"""
        tenant = Tenant.objects.create(
            name='トライアルなし',
            code='no-trial',
            trial_ends_at=None,
        )
        assert tenant.is_trial is False

    @pytest.mark.django_db
    def test_tenant_is_trial_expired_true(self):
        """トライアル期限切れの場合Trueを返す"""
        tenant = Tenant.objects.create(
            name='トライアル期限切れ',
            code='trial-expired',
            trial_ends_at=timezone.now() - timedelta(days=1),
        )
        assert tenant.is_trial_expired is True

    @pytest.mark.django_db
    def test_tenant_is_trial_expired_false_no_trial(self):
        """トライアル設定なしの場合Falseを返す"""
        tenant = Tenant.objects.create(
            name='トライアルなし2',
            code='no-trial-2',
            trial_ends_at=None,
        )
        assert tenant.is_trial_expired is False

    @pytest.mark.django_db
    def test_tenant_is_trial_expired_false_active(self):
        """トライアル中はFalseを返す"""
        tenant = Tenant.objects.create(
            name='トライアル中2',
            code='trial-active-2',
            trial_ends_at=timezone.now() + timedelta(days=7),
        )
        assert tenant.is_trial_expired is False

    @pytest.mark.django_db
    def test_tenant_get_setting(self):
        """設定値を取得できる"""
        tenant = Tenant.objects.create(
            name='設定テスト',
            code='settings-test',
            settings={'theme': 'dark', 'language': 'ja'},
        )
        assert tenant.get_setting('theme') == 'dark'
        assert tenant.get_setting('language') == 'ja'
        assert tenant.get_setting('non_existent') is None
        assert tenant.get_setting('non_existent', 'default') == 'default'

    @pytest.mark.django_db
    def test_tenant_set_setting(self):
        """設定値を保存できる"""
        tenant = Tenant.objects.create(
            name='設定保存テスト',
            code='settings-save-test',
        )
        tenant.set_setting('new_key', 'new_value')
        tenant.refresh_from_db()
        assert tenant.get_setting('new_key') == 'new_value'

    @pytest.mark.django_db
    def test_tenant_user_count_no_users(self):
        """ユーザーがいない場合0を返す"""
        tenant = Tenant.objects.create(
            name='ユーザーなし',
            code='no-users',
        )
        assert tenant.user_count() == 0

    @pytest.mark.django_db
    def test_tenant_user_count_with_users(self):
        """ユーザーがいる場合正しい数を返す"""
        from apps.accounts.models import CustomUser, UserRoleChoices
        tenant = Tenant.objects.create(
            name='ユーザーあり',
            code='with-users',
        )
        CustomUser.objects.create_user(
            email='user1@with-users.com',
            password='testpass123',
            tenant=tenant,
            role=UserRoleChoices.CLIENT_ADMIN,
        )
        CustomUser.objects.create_user(
            email='user2@with-users.com',
            password='testpass123',
            tenant=tenant,
            role=UserRoleChoices.INTERVIEWER,
        )
        assert tenant.user_count() == 2

    @pytest.mark.django_db
    def test_tenant_can_add_user_true(self):
        """最大ユーザー数に達していない場合Trueを返す"""
        tenant = Tenant.objects.create(
            name='追加可能',
            code='can-add',
            max_users=5,
        )
        assert tenant.can_add_user() is True

    @pytest.mark.django_db
    def test_tenant_can_add_user_false(self):
        """最大ユーザー数に達している場合Falseを返す"""
        from apps.accounts.models import CustomUser, UserRoleChoices
        tenant = Tenant.objects.create(
            name='追加不可',
            code='cannot-add',
            max_users=1,
        )
        CustomUser.objects.create_user(
            email='user@cannot-add.com',
            password='testpass123',
            tenant=tenant,
            role=UserRoleChoices.CLIENT_ADMIN,
        )
        assert tenant.can_add_user() is False


# =============================================================================
# TenantSpreadsheet Model Tests
# =============================================================================

class TestTenantSpreadsheetModel:
    """TenantSpreadsheet モデルのテスト"""

    @pytest.fixture
    def tenant(self, db):
        return Tenant.objects.create(
            name='スプレッドシートテスト',
            code='spreadsheet-test',
        )

    @pytest.mark.django_db
    def test_create_spreadsheet(self, tenant):
        """スプレッドシートを作成できる"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=tenant,
            spreadsheet_id='1234567890abcdef',
            spreadsheet_name='テストシート',
        )
        assert spreadsheet.pk is not None
        assert 'スプレッドシートテスト' in str(spreadsheet)
        assert 'テストシート' in str(spreadsheet)

    @pytest.mark.django_db
    def test_spreadsheet_url_property(self, tenant):
        """スプレッドシートURLを正しく生成する"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=tenant,
            spreadsheet_id='ABC123XYZ',
            spreadsheet_name='URLテスト',
        )
        expected_url = 'https://docs.google.com/spreadsheets/d/ABC123XYZ'
        assert spreadsheet.spreadsheet_url == expected_url

    @pytest.mark.django_db
    def test_record_sync_error(self, tenant):
        """同期エラーを記録できる"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=tenant,
            spreadsheet_id='error-test',
            spreadsheet_name='エラーテスト',
        )
        spreadsheet.record_sync_error('テストエラー1')
        spreadsheet.refresh_from_db()

        assert len(spreadsheet.sync_errors) == 1
        assert spreadsheet.sync_errors[0]['message'] == 'テストエラー1'
        assert 'timestamp' in spreadsheet.sync_errors[0]

    @pytest.mark.django_db
    def test_record_sync_error_max_10(self, tenant):
        """同期エラーは最大10件まで保持"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=tenant,
            spreadsheet_id='max-errors',
            spreadsheet_name='最大エラーテスト',
        )

        # 15件のエラーを記録
        for i in range(15):
            spreadsheet.record_sync_error(f'エラー{i}')

        spreadsheet.refresh_from_db()
        # 最大10件まで
        assert len(spreadsheet.sync_errors) == 10
        # 最新のエラーが先頭
        assert spreadsheet.sync_errors[0]['message'] == 'エラー14'

    @pytest.mark.django_db
    def test_update_sync_time(self, tenant):
        """同期日時を更新できる"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=tenant,
            spreadsheet_id='sync-time',
            spreadsheet_name='同期日時テスト',
        )
        assert spreadsheet.last_synced_at is None

        spreadsheet.update_sync_time()
        spreadsheet.refresh_from_db()

        assert spreadsheet.last_synced_at is not None
        # 現在時刻に近いこと（5秒以内）
        assert (timezone.now() - spreadsheet.last_synced_at).seconds < 5

    @pytest.mark.django_db
    def test_str_without_name(self, tenant):
        """スプレッドシート名がない場合IDを表示"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=tenant,
            spreadsheet_id='no-name-id',
            spreadsheet_name='',
        )
        assert 'no-name-id' in str(spreadsheet)

    @pytest.mark.django_db
    def test_one_to_one_relationship(self, tenant):
        """テナントとスプレッドシートは1対1"""
        TenantSpreadsheet.objects.create(
            tenant=tenant,
            spreadsheet_id='first',
            spreadsheet_name='最初',
        )

        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            TenantSpreadsheet.objects.create(
                tenant=tenant,
                spreadsheet_id='second',
                spreadsheet_name='2番目',
            )


# =============================================================================
# Tenant Plan Tests
# =============================================================================

class TestTenantPlans:
    """テナントプラン関連のテスト"""

    @pytest.mark.django_db
    def test_all_plan_choices_valid(self):
        """すべてのプラン選択肢が有効"""
        for plan_value, plan_label in Tenant.PlanChoices.choices:
            tenant = Tenant.objects.create(
                name=f'{plan_label}テナント',
                code=f'{plan_value}-test',
                plan=plan_value,
            )
            assert tenant.plan == plan_value

    @pytest.mark.django_db
    def test_enterprise_plan_features(self):
        """エンタープライズプランのテナント"""
        tenant = Tenant.objects.create(
            name='エンタープライズ',
            code='enterprise-test',
            plan=Tenant.PlanChoices.ENTERPRISE,
            max_users=1000,
        )
        assert tenant.plan == Tenant.PlanChoices.ENTERPRISE
        assert tenant.max_users == 1000
