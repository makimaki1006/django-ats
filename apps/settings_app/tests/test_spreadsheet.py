"""
スプレッドシート連携機能のユニットテスト

逆証明によるロジック検証:
1. モデル制約の検証
2. フォームバリデーションの検証
3. 同期サービスのロジック検証
"""

import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.settings_app.models import SpreadsheetConnection, SyncStatusChoices
from apps.settings_app.forms import SpreadsheetConnectionForm


User = get_user_model()


class SpreadsheetConnectionModelTest(TestCase):
    """モデルのロジック検証"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_model_creation(self):
        """モデル作成の基本検証"""
        connection = SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='test123',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
            spreadsheet_name='テストシート',
            credentials_json='{"type":"service_account"}',
        )

        self.assertEqual(connection.tenant, self.tenant)
        self.assertEqual(connection.spreadsheet_id, 'test123')
        self.assertEqual(connection.sync_status, SyncStatusChoices.PENDING)
        self.assertTrue(connection.is_active)

    def test_unique_constraint(self):
        """同一テナント・同一スプレッドシートの重複禁止"""
        SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='test123',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
        )

        # 同じspreadsheet_idで作成しようとするとエラー
        # TenantBaseModelのsave()でfull_clean()が呼ばれるためValidationError
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            SpreadsheetConnection.objects.create(
                tenant=self.tenant,
                spreadsheet_id='test123',
                spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
            )

    def test_different_tenant_same_spreadsheet_allowed(self):
        """異なるテナントなら同じスプレッドシートID可"""
        tenant2 = Tenant.objects.create(
            name='テストテナント2',
            code='test-tenant-2',
            is_active=True,
        )

        SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='test123',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
        )

        # 別テナントなら同じIDでOK
        connection2 = SpreadsheetConnection.objects.create(
            tenant=tenant2,
            spreadsheet_id='test123',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
        )
        self.assertIsNotNone(connection2.id)

    def test_mark_synced(self):
        """mark_synced()のロジック検証"""
        connection = SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='test123',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
            sync_status=SyncStatusChoices.ERROR,
            last_sync_error='前回エラー',
        )

        connection.mark_synced()
        connection.refresh_from_db()

        self.assertEqual(connection.sync_status, SyncStatusChoices.CONNECTED)
        self.assertEqual(connection.last_sync_error, '')
        self.assertIsNotNone(connection.last_synced_at)

    def test_mark_error(self):
        """mark_error()のロジック検証"""
        connection = SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='test123',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
        )

        connection.mark_error('接続失敗')
        connection.refresh_from_db()

        self.assertEqual(connection.sync_status, SyncStatusChoices.ERROR)
        self.assertEqual(connection.last_sync_error, '接続失敗')

    def test_is_connected_property(self):
        """is_connected プロパティの検証"""
        connection = SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='test123',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
        )

        self.assertFalse(connection.is_connected)  # PENDING

        connection.sync_status = SyncStatusChoices.CONNECTED
        connection.save()
        self.assertTrue(connection.is_connected)

        connection.sync_status = SyncStatusChoices.ERROR
        connection.save()
        self.assertFalse(connection.is_connected)


class SpreadsheetConnectionFormTest(TestCase):
    """フォームバリデーションの検証"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.valid_credentials = json.dumps({
            'type': 'service_account',
            'project_id': 'test-project',
            'private_key': '-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n',
            'client_email': 'test@test.iam.gserviceaccount.com',
        })

    def test_valid_form(self):
        """正常なフォームデータ"""
        form = SpreadsheetConnectionForm(
            data={
                'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/1abc123xyz/edit',
                'spreadsheet_name': 'テストシート',
                'credentials_json': self.valid_credentials,
                'is_active': True,
                'sync_candidates': True,
                'sync_jobs': True,
                'sync_applications': True,
                'sync_interviews': True,
                'auto_sync_enabled': True,
                'sync_interval_minutes': 5,
            },
            tenant=self.tenant,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.spreadsheet_id, '1abc123xyz')

    def test_invalid_url_format(self):
        """不正なURL形式の検証"""
        form = SpreadsheetConnectionForm(
            data={
                'spreadsheet_url': 'https://example.com/not-a-spreadsheet',
                'credentials_json': self.valid_credentials,
            },
            tenant=self.tenant,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('spreadsheet_url', form.errors)

    def test_invalid_credentials_json(self):
        """不正なJSON形式の検証"""
        form = SpreadsheetConnectionForm(
            data={
                'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/1abc123xyz/edit',
                'credentials_json': 'not valid json',
            },
            tenant=self.tenant,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('credentials_json', form.errors)

    def test_missing_required_fields_in_credentials(self):
        """認証情報の必須フィールド欠落"""
        incomplete_credentials = json.dumps({
            'type': 'service_account',
            # project_id, private_key, client_email が欠落
        })

        form = SpreadsheetConnectionForm(
            data={
                'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/1abc123xyz/edit',
                'credentials_json': incomplete_credentials,
            },
            tenant=self.tenant,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('credentials_json', form.errors)

    def test_spreadsheet_id_extraction_variations(self):
        """様々なURL形式からのID抽出"""
        test_cases = [
            ('https://docs.google.com/spreadsheets/d/1abc123xyz/edit', '1abc123xyz'),
            ('https://docs.google.com/spreadsheets/d/1abc123xyz/edit#gid=0', '1abc123xyz'),
            ('https://docs.google.com/spreadsheets/d/1abc-_123xyz/edit', '1abc-_123xyz'),
        ]

        for url, expected_id in test_cases:
            form = SpreadsheetConnectionForm(
                data={
                    'spreadsheet_url': url,
                    'credentials_json': self.valid_credentials,
                },
                tenant=self.tenant,
            )
            if form.is_valid():
                self.assertEqual(form.spreadsheet_id, expected_id, f"URL: {url}")

    def test_duplicate_spreadsheet_validation(self):
        """重複スプレッドシートの検証"""
        # 既存の接続を作成
        SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='1abc123xyz',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/1abc123xyz/edit',
        )

        # 同じIDで新規作成しようとする
        form = SpreadsheetConnectionForm(
            data={
                'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/1abc123xyz/edit',
                'credentials_json': self.valid_credentials,
            },
            tenant=self.tenant,
        )

        self.assertFalse(form.is_valid())


class SpreadsheetSyncServiceTest(TestCase):
    """同期サービスのロジック検証"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='test123',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
            credentials_json=json.dumps({
                'type': 'service_account',
                'project_id': 'test',
                'private_key': 'test',
                'client_email': 'test@test.iam.gserviceaccount.com',
            }),
        )

    @patch('apps.core.services.spreadsheet_sync.SpreadsheetSyncService._get_client')
    def test_test_connection_success(self, mock_get_client):
        """接続テスト成功のロジック"""
        from apps.core.services import SpreadsheetSyncService

        # モックの設定
        mock_spreadsheet = Mock()
        mock_spreadsheet.title = 'テストスプレッドシート'
        mock_client = Mock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_get_client.return_value = mock_client

        service = SpreadsheetSyncService(self.connection)
        success, message = service.test_connection()

        self.assertTrue(success)
        self.assertIn('テストスプレッドシート', message)

        # 接続後の状態確認
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.sync_status, SyncStatusChoices.CONNECTED)
        self.assertEqual(self.connection.spreadsheet_name, 'テストスプレッドシート')

    @patch('apps.core.services.spreadsheet_sync.SpreadsheetSyncService._get_client')
    def test_test_connection_failure(self, mock_get_client):
        """接続テスト失敗のロジック"""
        from apps.core.services import SpreadsheetSyncService

        mock_get_client.side_effect = Exception('認証エラー')

        service = SpreadsheetSyncService(self.connection)
        success, message = service.test_connection()

        self.assertFalse(success)
        self.assertIn('認証エラー', message)

        # エラー後の状態確認
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.sync_status, SyncStatusChoices.ERROR)

    def test_parse_date_logic(self):
        """日付パースのロジック検証"""
        from apps.core.services import SpreadsheetSyncService

        service = SpreadsheetSyncService(self.connection)

        # 正常ケース
        self.assertIsNotNone(service._parse_date('2024-12-01'))
        self.assertIsNotNone(service._parse_date('2024-12-01T09:00:00+09:00'))

        # 空・無効ケース
        self.assertIsNone(service._parse_date(''))
        self.assertIsNone(service._parse_date(None))
        self.assertIsNone(service._parse_date('invalid'))

    def test_parse_int_logic(self):
        """整数パースのロジック検証"""
        from apps.core.services import SpreadsheetSyncService

        service = SpreadsheetSyncService(self.connection)

        # 正常ケース
        self.assertEqual(service._parse_int('123'), 123)
        self.assertEqual(service._parse_int('123.5'), 123)  # 小数は切り捨て

        # 空・無効ケース
        self.assertIsNone(service._parse_int(''))
        self.assertIsNone(service._parse_int(None))
        self.assertIsNone(service._parse_int('abc'))


class SpreadsheetViewsTest(TestCase):
    """ビューのロジック検証"""

    def setUp(self):
        self.factory = RequestFactory()
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant,
        )

    def test_index_view_without_connection(self):
        """接続なしの設定画面"""
        from apps.settings_app.views import SettingsIndexView

        request = self.factory.get('/settings/')
        request.user = self.user
        request.tenant = self.tenant

        view = SettingsIndexView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        # has_spreadsheet が False であることを確認
        self.assertFalse(response.context_data.get('has_spreadsheet'))

    def test_index_view_with_connection(self):
        """接続ありの設定画面"""
        from apps.settings_app.views import SettingsIndexView

        SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='test123',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test123/edit',
        )

        request = self.factory.get('/settings/')
        request.user = self.user
        request.tenant = self.tenant

        view = SettingsIndexView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data.get('has_spreadsheet'))
        self.assertIsNotNone(response.context_data.get('spreadsheet_connection'))
