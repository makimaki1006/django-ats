"""Django ATS - テナントオンボーディングサービス

新規テナント登録時のスプレッドシート作成・設定を管理。
"""

import logging
from typing import Optional

from django.conf import settings
from django.db import transaction

from apps.tenants.models import Tenant, TenantSpreadsheet
from .client import SheetsClient
from .exceptions import SheetsError, SheetsAuthError

logger = logging.getLogger(__name__)


class TenantOnboardingService:
    """テナントオンボーディングサービス

    新規テナント登録時に以下を実行:
    1. テンプレートスプレッドシートをコピー
    2. テナント用にリネーム
    3. TenantSpreadsheetレコードを作成
    4. 初期設定を書き込み

    使用例:
        service = TenantOnboardingService()
        spreadsheet = service.setup_tenant_spreadsheet(tenant)
    """

    def __init__(self):
        self.client = SheetsClient()

    def setup_tenant_spreadsheet(
        self,
        tenant: Tenant,
        admin_email: Optional[str] = None
    ) -> TenantSpreadsheet:
        """テナント用スプレッドシートをセットアップ

        Args:
            tenant: 対象テナント
            admin_email: 管理者メールアドレス（共有用、省略可）

        Returns:
            TenantSpreadsheet: 作成されたスプレッドシート紐付けレコード

        Raises:
            SheetsError: スプレッドシート作成に失敗した場合
        """
        # 既存のスプレッドシートがあればエラー
        if hasattr(tenant, 'spreadsheet') and tenant.spreadsheet:
            raise SheetsError(
                f"テナント '{tenant.name}' には既にスプレッドシートが設定されています"
            )

        # Google Sheets連携が無効な場合
        if not settings.GOOGLE_SHEETS_ENABLED:
            raise SheetsAuthError(
                "Google Sheets連携が無効です。GOOGLE_SHEETS_ENABLED=Trueを設定してください。"
            )

        # テンプレートIDが未設定の場合
        template_id = settings.GOOGLE_TEMPLATE_SPREADSHEET_ID
        if not template_id:
            raise SheetsError(
                "テンプレートスプレッドシートIDが設定されていません。"
                "GOOGLE_TEMPLATE_SPREADSHEET_IDを設定してください。"
            )

        try:
            # 1. テンプレートをコピー
            spreadsheet_name = f"ATS - {tenant.name}"
            new_spreadsheet = self.client.copy_spreadsheet(
                template_id,
                spreadsheet_name
            )
            spreadsheet_id = new_spreadsheet.id

            logger.info(
                f"テナント '{tenant.name}' 用スプレッドシートを作成: {spreadsheet_id}"
            )

            # 2. 管理者に共有（指定がある場合）
            if admin_email:
                self.client.share_spreadsheet(
                    spreadsheet_id,
                    admin_email,
                    role='writer'
                )
                logger.info(f"スプレッドシートを共有: {admin_email}")

            # 3. TenantSpreadsheetレコードを作成
            with transaction.atomic():
                tenant_spreadsheet = TenantSpreadsheet.objects.create(
                    tenant=tenant,
                    spreadsheet_id=spreadsheet_id,
                    spreadsheet_name=spreadsheet_name,
                    is_active=True
                )

            # 4. 初期設定を書き込み
            self._write_initial_settings(spreadsheet_id, tenant)

            logger.info(
                f"テナント '{tenant.name}' のオンボーディング完了"
            )

            return tenant_spreadsheet

        except Exception as e:
            logger.error(
                f"テナント '{tenant.name}' のスプレッドシート作成に失敗: {e}"
            )
            raise SheetsError(
                f"スプレッドシートの作成に失敗しました: {e}",
                original_error=e
            )

    def _write_initial_settings(self, spreadsheet_id: str, tenant: Tenant):
        """初期設定をスプレッドシートに書き込み

        Args:
            spreadsheet_id: スプレッドシートID
            tenant: テナント
        """
        try:
            spreadsheet = self.client.open_spreadsheet(spreadsheet_id)
            settings_sheet = self.client.get_or_create_worksheet(
                spreadsheet,
                '設定'
            )

            # ヘッダー行
            self.client.update_row(settings_sheet, 1, ['key', 'value', 'description'])

            # 初期設定値
            initial_settings = [
                ['company_name', tenant.name, '会社名'],
                ['tenant_code', tenant.code, 'テナントコード'],
                ['timezone', 'Asia/Tokyo', 'タイムゾーン'],
                ['date_format', 'YYYY-MM-DD', '日付形式'],
                ['currency', 'JPY', '通貨'],
                ['default_interview_duration', '60', 'デフォルト面接時間（分）'],
                ['notification_email', '', '通知先メールアドレス'],
            ]

            self.client.append_rows(settings_sheet, initial_settings)
            logger.info(f"初期設定を書き込み: {spreadsheet_id}")

        except Exception as e:
            logger.warning(f"初期設定の書き込みに失敗（続行）: {e}")

    def verify_spreadsheet_access(self, tenant: Tenant) -> bool:
        """テナントのスプレッドシートへのアクセスを確認

        Args:
            tenant: 対象テナント

        Returns:
            bool: アクセス可能な場合True
        """
        if not hasattr(tenant, 'spreadsheet') or not tenant.spreadsheet:
            return False

        spreadsheet = tenant.spreadsheet
        if not spreadsheet.is_active:
            return False

        return self.client.test_connection(spreadsheet.spreadsheet_id)

    def disable_spreadsheet(self, tenant: Tenant):
        """テナントのスプレッドシート連携を無効化

        Args:
            tenant: 対象テナント
        """
        if hasattr(tenant, 'spreadsheet') and tenant.spreadsheet:
            tenant.spreadsheet.is_active = False
            tenant.spreadsheet.save(update_fields=['is_active', 'updated_at'])
            logger.info(f"テナント '{tenant.name}' のスプレッドシート連携を無効化")

    def enable_spreadsheet(self, tenant: Tenant):
        """テナントのスプレッドシート連携を有効化

        Args:
            tenant: 対象テナント
        """
        if hasattr(tenant, 'spreadsheet') and tenant.spreadsheet:
            tenant.spreadsheet.is_active = True
            tenant.spreadsheet.save(update_fields=['is_active', 'updated_at'])
            logger.info(f"テナント '{tenant.name}' のスプレッドシート連携を有効化")


def get_tenant_repository_factory(tenant: Tenant):
    """テナントのリポジトリファクトリを取得

    Args:
        tenant: 対象テナント

    Returns:
        SheetsRepositoryFactory: リポジトリファクトリ

    Raises:
        SheetsError: スプレッドシートが設定されていない場合
    """
    from .repositories import SheetsRepositoryFactory

    if not hasattr(tenant, 'spreadsheet') or not tenant.spreadsheet:
        raise SheetsError(
            f"テナント '{tenant.name}' にはスプレッドシートが設定されていません"
        )

    spreadsheet = tenant.spreadsheet
    if not spreadsheet.is_active:
        raise SheetsError(
            f"テナント '{tenant.name}' のスプレッドシート連携は無効です"
        )

    return SheetsRepositoryFactory(spreadsheet.spreadsheet_id)
