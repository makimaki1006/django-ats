"""
Tenants アプリモデルテスト
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.tenants.models import Tenant, TenantSpreadsheet


class TenantModelTest(TestCase):
    """Tenantモデルテスト"""

    def test_create_tenant(self):
        """テナントを作成できる"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
            is_active=True,
        )
        self.assertEqual(tenant.name, 'テスト企業')
        self.assertEqual(tenant.code, 'test-corp')
        self.assertTrue(tenant.is_active)

    def test_tenant_str(self):
        """__str__はテナント名を返す"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
        )
        self.assertEqual(str(tenant), 'テスト企業')

    def test_tenant_default_plan(self):
        """デフォルトプランはfree"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
        )
        self.assertEqual(tenant.plan, Tenant.PlanChoices.FREE)

    def test_tenant_default_max_users(self):
        """デフォルト最大ユーザー数は5"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
        )
        self.assertEqual(tenant.max_users, 5)

    def test_is_trial_true(self):
        """トライアル中の場合Trueを返す"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
            trial_ends_at=timezone.now() + timedelta(days=7),
        )
        self.assertTrue(tenant.is_trial)

    def test_is_trial_false_no_trial(self):
        """トライアル設定なしの場合Falseを返す"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
        )
        self.assertFalse(tenant.is_trial)

    def test_is_trial_false_expired(self):
        """トライアル期限切れの場合Falseを返す"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
            trial_ends_at=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(tenant.is_trial)

    def test_is_trial_expired_true(self):
        """トライアル期限切れの場合Trueを返す"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
            trial_ends_at=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(tenant.is_trial_expired)

    def test_get_setting(self):
        """設定値を取得できる"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
            settings={'key': 'value'},
        )
        self.assertEqual(tenant.get_setting('key'), 'value')
        self.assertIsNone(tenant.get_setting('nonexistent'))
        self.assertEqual(tenant.get_setting('nonexistent', 'default'), 'default')

    def test_set_setting(self):
        """設定値を保存できる"""
        tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
        )
        tenant.set_setting('new_key', 'new_value')
        tenant.refresh_from_db()
        self.assertEqual(tenant.get_setting('new_key'), 'new_value')

    def test_code_unique(self):
        """コードはユニーク"""
        Tenant.objects.create(name='テナント1', code='unique-code')
        with self.assertRaises(Exception):
            Tenant.objects.create(name='テナント2', code='unique-code')


class TenantSpreadsheetModelTest(TestCase):
    """TenantSpreadsheetモデルテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テスト企業',
            code='test-corp',
        )

    def test_create_spreadsheet(self):
        """スプレッドシート接続を作成できる"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=self.tenant,
            spreadsheet_id='1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms',
            spreadsheet_name='テストシート',
        )
        self.assertEqual(spreadsheet.spreadsheet_name, 'テストシート')
        self.assertTrue(spreadsheet.is_active)

    def test_spreadsheet_url(self):
        """スプレッドシートURLが正しく生成される"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=self.tenant,
            spreadsheet_id='abc123',
        )
        self.assertEqual(
            spreadsheet.spreadsheet_url,
            'https://docs.google.com/spreadsheets/d/abc123'
        )

    def test_record_sync_error(self):
        """同期エラーを記録できる"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=self.tenant,
            spreadsheet_id='abc123',
        )
        spreadsheet.record_sync_error('テストエラー')
        spreadsheet.refresh_from_db()
        self.assertEqual(len(spreadsheet.sync_errors), 1)
        self.assertEqual(spreadsheet.sync_errors[0]['message'], 'テストエラー')

    def test_record_sync_error_max_10(self):
        """同期エラーは最大10件保持"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=self.tenant,
            spreadsheet_id='abc123',
        )
        for i in range(15):
            spreadsheet.record_sync_error(f'エラー{i}')

        spreadsheet.refresh_from_db()
        self.assertEqual(len(spreadsheet.sync_errors), 10)
        # 最新のエラーが先頭
        self.assertEqual(spreadsheet.sync_errors[0]['message'], 'エラー14')

    def test_update_sync_time(self):
        """同期日時を更新できる"""
        spreadsheet = TenantSpreadsheet.objects.create(
            tenant=self.tenant,
            spreadsheet_id='abc123',
        )
        self.assertIsNone(spreadsheet.last_synced_at)

        spreadsheet.update_sync_time()
        spreadsheet.refresh_from_db()
        self.assertIsNotNone(spreadsheet.last_synced_at)

    def test_one_spreadsheet_per_tenant(self):
        """1テナントに1スプレッドシートのみ"""
        TenantSpreadsheet.objects.create(
            tenant=self.tenant,
            spreadsheet_id='sheet1',
        )
        with self.assertRaises(Exception):
            TenantSpreadsheet.objects.create(
                tenant=self.tenant,
                spreadsheet_id='sheet2',
            )
