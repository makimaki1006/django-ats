"""Django ATS - Google Sheetsクライアント

gspreadをラップしたSheetsクライアント。
認証、エラーハンドリング、リトライを統合管理。
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache

from .exceptions import (
    SheetsAuthError,
    SheetsError,
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsRateLimitError,
)

logger = logging.getLogger(__name__)


class SheetsClient:
    """Google Sheetsクライアント

    テナントごとのスプレッドシート操作を提供。
    シングルトンパターンで認証を共有。

    使用例:
        # クライアント取得
        client = SheetsClient()

        # スプレッドシートを開く
        spreadsheet = client.open_spreadsheet("spreadsheet_id")

        # シートを取得
        sheet = client.get_worksheet(spreadsheet, "候補者")

        # 全データ取得
        data = client.get_all_records(sheet)

        # 行追加
        client.append_row(sheet, ["値1", "値2", "値3"])
    """

    _instance = None
    _gspread_client = None

    def __new__(cls):
        """シングルトンパターン"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初期化（認証は遅延実行）"""
        self._initialized = getattr(self, '_initialized', False)
        if self._initialized:
            return
        self._initialized = True

    @property
    def client(self):
        """gspreadクライアントを取得（遅延認証）"""
        if self._gspread_client is None:
            self._gspread_client = self._authenticate()
        return self._gspread_client

    def _authenticate(self):
        """Google Sheets APIの認証を実行

        Returns:
            gspread.Client: 認証済みクライアント

        Raises:
            SheetsAuthError: 認証に失敗した場合
        """
        if not settings.GOOGLE_SHEETS_ENABLED:
            raise SheetsAuthError("Google Sheets連携が無効です。GOOGLE_SHEETS_ENABLED=Trueを設定してください。")

        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError as e:
            raise SheetsAuthError(
                "必要なライブラリがインストールされていません。"
                "pip install gspread google-auth を実行してください。",
                original_error=e
            )

        # 認証情報を取得
        credentials_info = self._get_credentials_info()

        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive',
            ]
            credentials = Credentials.from_service_account_info(
                credentials_info,
                scopes=scopes
            )
            client = gspread.authorize(credentials)
            logger.info("Google Sheets API認証成功")
            return client
        except Exception as e:
            raise SheetsAuthError(
                "Google Sheets API認証に失敗しました。認証情報を確認してください。",
                original_error=e
            )

    def _get_credentials_info(self) -> Dict[str, Any]:
        """認証情報を取得

        環境変数から認証情報を取得。
        GOOGLE_CREDENTIALS_JSON（JSON文字列）を優先し、
        なければGOOGLE_CREDENTIALS_FILE（ファイルパス）を使用。

        Returns:
            dict: サービスアカウント認証情報

        Raises:
            SheetsAuthError: 認証情報が設定されていない場合
        """
        # JSON文字列から取得
        credentials_json = settings.GOOGLE_CREDENTIALS_JSON
        if credentials_json:
            try:
                return json.loads(credentials_json)
            except json.JSONDecodeError as e:
                raise SheetsAuthError(
                    "GOOGLE_CREDENTIALS_JSONのJSON形式が不正です。",
                    original_error=e
                )

        # ファイルパスから取得
        credentials_file = settings.GOOGLE_CREDENTIALS_FILE
        if credentials_file:
            try:
                with open(credentials_file, 'r') as f:
                    return json.load(f)
            except FileNotFoundError:
                raise SheetsAuthError(
                    f"認証情報ファイルが見つかりません: {credentials_file}"
                )
            except json.JSONDecodeError as e:
                raise SheetsAuthError(
                    f"認証情報ファイルのJSON形式が不正です: {credentials_file}",
                    original_error=e
                )

        raise SheetsAuthError(
            "Google Sheets認証情報が設定されていません。"
            "GOOGLE_CREDENTIALS_JSONまたはGOOGLE_CREDENTIALS_FILEを設定してください。"
        )

    def _with_retry(self, operation, *args, **kwargs):
        """リトライ付きで操作を実行

        Args:
            operation: 実行する関数
            *args, **kwargs: 関数に渡す引数

        Returns:
            操作の戻り値

        Raises:
            SheetsError: リトライ回数を超えた場合
        """
        retry_count = settings.GOOGLE_SHEETS_RETRY_COUNT
        retry_delay = settings.GOOGLE_SHEETS_RETRY_DELAY

        last_error = None
        for attempt in range(retry_count):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # レート制限の場合はリトライ
                if 'quota' in error_str or 'rate limit' in error_str:
                    if attempt < retry_count - 1:
                        wait_time = retry_delay * (2 ** attempt)  # 指数バックオフ
                        logger.warning(
                            f"レート制限検出。{wait_time}秒後にリトライ "
                            f"(試行 {attempt + 1}/{retry_count})"
                        )
                        time.sleep(wait_time)
                        continue
                    raise SheetsRateLimitError(
                        "APIレート制限に達しました。しばらく待ってから再試行してください。",
                        retry_after=60,
                        original_error=e
                    )

                # 権限エラー
                if 'permission' in error_str or 'forbidden' in error_str:
                    raise SheetsPermissionError(
                        "スプレッドシートへのアクセス権限がありません。"
                        "サービスアカウントに共有してください。",
                        original_error=e
                    )

                # 未発見エラー
                if 'not found' in error_str or 'spreadsheet not found' in error_str:
                    raise SheetsNotFoundError(
                        "スプレッドシートが見つかりません。IDを確認してください。",
                        original_error=e
                    )

                # その他のエラーはそのまま送出
                raise SheetsError(
                    f"Sheets操作中にエラーが発生しました: {e}",
                    original_error=e
                )

        raise SheetsError(
            f"操作が{retry_count}回失敗しました",
            original_error=last_error
        )

    # ==========================================================================
    # スプレッドシート操作
    # ==========================================================================

    def open_spreadsheet(self, spreadsheet_id: str):
        """スプレッドシートを開く

        Args:
            spreadsheet_id: スプレッドシートID

        Returns:
            gspread.Spreadsheet: スプレッドシートオブジェクト
        """
        cache_key = f"sheets:spreadsheet:{spreadsheet_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        spreadsheet = self._with_retry(
            self.client.open_by_key,
            spreadsheet_id
        )

        cache.set(cache_key, spreadsheet, settings.GOOGLE_SHEETS_CACHE_TTL)
        return spreadsheet

    def copy_spreadsheet(self, spreadsheet_id: str, title: str, folder_id: str = None):
        """スプレッドシートをコピー

        新規テナント用にテンプレートをコピーする際に使用。

        Args:
            spreadsheet_id: コピー元スプレッドシートID
            title: 新しいスプレッドシート名
            folder_id: コピー先フォルダID（オプション）

        Returns:
            gspread.Spreadsheet: 新しいスプレッドシート
        """
        spreadsheet = self.open_spreadsheet(spreadsheet_id)
        new_spreadsheet = self._with_retry(
            self.client.copy,
            spreadsheet.id,
            title=title,
            copy_permissions=False,
            folder_id=folder_id
        )
        logger.info(f"スプレッドシートをコピー: {title} (ID: {new_spreadsheet.id})")
        return new_spreadsheet

    def share_spreadsheet(self, spreadsheet_id: str, email: str, role: str = 'writer'):
        """スプレッドシートを共有

        Args:
            spreadsheet_id: スプレッドシートID
            email: 共有先メールアドレス
            role: 権限 ('reader', 'writer', 'owner')
        """
        spreadsheet = self.open_spreadsheet(spreadsheet_id)
        self._with_retry(
            spreadsheet.share,
            email,
            perm_type='user',
            role=role
        )
        logger.info(f"スプレッドシートを共有: {email} ({role})")

    # ==========================================================================
    # ワークシート操作
    # ==========================================================================

    def get_worksheet(self, spreadsheet, sheet_name: str):
        """シートを取得

        Args:
            spreadsheet: スプレッドシートオブジェクト
            sheet_name: シート名

        Returns:
            gspread.Worksheet: ワークシートオブジェクト
        """
        try:
            return spreadsheet.worksheet(sheet_name)
        except Exception as e:
            raise SheetsNotFoundError(
                f"シート '{sheet_name}' が見つかりません。",
                original_error=e
            )

    def get_or_create_worksheet(self, spreadsheet, sheet_name: str, rows: int = 1000, cols: int = 26):
        """シートを取得（なければ作成）

        Args:
            spreadsheet: スプレッドシートオブジェクト
            sheet_name: シート名
            rows: 行数（新規作成時）
            cols: 列数（新規作成時）

        Returns:
            gspread.Worksheet: ワークシートオブジェクト
        """
        try:
            return spreadsheet.worksheet(sheet_name)
        except Exception:
            worksheet = self._with_retry(
                spreadsheet.add_worksheet,
                title=sheet_name,
                rows=rows,
                cols=cols
            )
            logger.info(f"新しいシートを作成: {sheet_name}")
            return worksheet

    # ==========================================================================
    # データ操作
    # ==========================================================================

    def get_all_records(self, worksheet) -> List[Dict[str, Any]]:
        """シートの全データを辞書リストとして取得

        1行目をヘッダーとして使用。

        Args:
            worksheet: ワークシートオブジェクト

        Returns:
            list[dict]: レコードのリスト
        """
        return self._with_retry(worksheet.get_all_records)

    def get_all_values(self, worksheet) -> List[List[Any]]:
        """シートの全データを2次元リストとして取得

        Args:
            worksheet: ワークシートオブジェクト

        Returns:
            list[list]: 値の2次元リスト
        """
        return self._with_retry(worksheet.get_all_values)

    def append_row(self, worksheet, values: List[Any], value_input_option: str = 'USER_ENTERED'):
        """行を末尾に追加

        Args:
            worksheet: ワークシートオブジェクト
            values: 追加する値のリスト
            value_input_option: 値の解釈方法 ('RAW' or 'USER_ENTERED')

        Returns:
            dict: 更新結果
        """
        return self._with_retry(
            worksheet.append_row,
            values,
            value_input_option=value_input_option
        )

    def append_rows(self, worksheet, values: List[List[Any]], value_input_option: str = 'USER_ENTERED'):
        """複数行を末尾に追加

        Args:
            worksheet: ワークシートオブジェクト
            values: 追加する値の2次元リスト
            value_input_option: 値の解釈方法

        Returns:
            dict: 更新結果
        """
        return self._with_retry(
            worksheet.append_rows,
            values,
            value_input_option=value_input_option
        )

    def update_row(self, worksheet, row_number: int, values: List[Any], value_input_option: str = 'USER_ENTERED'):
        """特定の行を更新

        Args:
            worksheet: ワークシートオブジェクト
            row_number: 行番号（1始まり）
            values: 更新する値のリスト
            value_input_option: 値の解釈方法

        Returns:
            dict: 更新結果
        """
        # A:Z範囲で更新（26列）
        range_notation = f"A{row_number}:Z{row_number}"
        return self._with_retry(
            worksheet.update,
            range_notation,
            [values],
            value_input_option=value_input_option
        )

    def delete_row(self, worksheet, row_number: int):
        """特定の行を削除

        Args:
            worksheet: ワークシートオブジェクト
            row_number: 行番号（1始まり）
        """
        return self._with_retry(
            worksheet.delete_rows,
            row_number
        )

    def find_row(self, worksheet, column: int, value: Any) -> Optional[int]:
        """特定の値を持つ行を検索

        Args:
            worksheet: ワークシートオブジェクト
            column: 検索する列番号（1始まり）
            value: 検索する値

        Returns:
            int or None: 行番号（見つからない場合はNone）
        """
        try:
            cell = self._with_retry(
                worksheet.find,
                str(value),
                in_column=column
            )
            return cell.row if cell else None
        except Exception:
            return None

    def clear_worksheet(self, worksheet):
        """シートの内容をクリア（ヘッダー以外）

        Args:
            worksheet: ワークシートオブジェクト
        """
        # 2行目以降をクリア
        return self._with_retry(worksheet.clear)

    def batch_update(self, worksheet, data: List[Dict[str, Any]]):
        """複数セルを一括更新

        Args:
            worksheet: ワークシートオブジェクト
            data: 更新データのリスト
                  [{'range': 'A1:B2', 'values': [[1, 2], [3, 4]]}, ...]
        """
        return self._with_retry(
            worksheet.batch_update,
            data
        )

    # ==========================================================================
    # ヘルパーメソッド
    # ==========================================================================

    def is_available(self) -> bool:
        """Sheets連携が利用可能かチェック

        Returns:
            bool: 利用可能な場合True
        """
        if not settings.GOOGLE_SHEETS_ENABLED:
            return False
        try:
            self._get_credentials_info()
            return True
        except SheetsAuthError:
            return False

    def test_connection(self, spreadsheet_id: str) -> bool:
        """接続テスト

        Args:
            spreadsheet_id: テストするスプレッドシートID

        Returns:
            bool: 接続成功の場合True
        """
        try:
            spreadsheet = self.open_spreadsheet(spreadsheet_id)
            _ = spreadsheet.title  # 読み取りテスト
            return True
        except SheetsError:
            return False
