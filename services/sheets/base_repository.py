"""Django ATS - Sheetsリポジトリ基底クラス

スプレッドシートへのCRUD操作を抽象化。
各モデル用リポジトリはこのクラスを継承。
"""

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from django.utils import timezone

from .client import SheetsClient
from .exceptions import SheetsNotFoundError, SheetsValidationError

logger = logging.getLogger(__name__)


class BaseSheetsRepository(ABC):
    """Sheetsリポジトリ基底クラス

    テンプレートメソッドパターンでCRUD操作を提供。
    サブクラスでsheet_name, columns, model_classを定義。

    使用例:
        class CandidateRepository(BaseSheetsRepository):
            sheet_name = '候補者'
            columns = ['id', 'name', 'email', ...]

            def to_row(self, data: dict) -> list:
                return [data.get('id'), data.get('name'), ...]

            def from_row(self, row: list) -> dict:
                return {'id': row[0], 'name': row[1], ...}
    """

    # サブクラスで定義必須
    sheet_name: str = None  # シート名
    columns: List[str] = None  # カラム名リスト（ヘッダー行）
    id_column: int = 1  # ID列（1始まり）

    def __init__(self, spreadsheet_id: str):
        """初期化

        Args:
            spreadsheet_id: 操作対象のスプレッドシートID
        """
        if not self.sheet_name:
            raise ValueError("sheet_nameを定義してください")
        if not self.columns:
            raise ValueError("columnsを定義してください")

        self.spreadsheet_id = spreadsheet_id
        self.client = SheetsClient()
        self._worksheet = None
        self._spreadsheet = None

    @property
    def spreadsheet(self):
        """スプレッドシートを取得（遅延ロード）"""
        if self._spreadsheet is None:
            self._spreadsheet = self.client.open_spreadsheet(self.spreadsheet_id)
        return self._spreadsheet

    @property
    def worksheet(self):
        """ワークシートを取得（遅延ロード）"""
        if self._worksheet is None:
            self._worksheet = self.client.get_or_create_worksheet(
                self.spreadsheet,
                self.sheet_name
            )
            self._ensure_headers()
        return self._worksheet

    def _ensure_headers(self):
        """ヘッダー行が存在しない場合は作成"""
        try:
            values = self.client.get_all_values(self._worksheet)
            if not values or values[0] != self.columns:
                # ヘッダー行を設定
                self.client.update_row(self._worksheet, 1, self.columns)
                logger.info(f"シート '{self.sheet_name}' にヘッダーを設定")
        except Exception as e:
            logger.warning(f"ヘッダー確認中にエラー: {e}")

    # ==========================================================================
    # 抽象メソッド（サブクラスで実装必須）
    # ==========================================================================

    @abstractmethod
    def to_row(self, data: Dict[str, Any]) -> List[Any]:
        """辞書データをスプレッドシートの行に変換

        Args:
            data: エンティティデータ（辞書）

        Returns:
            list: スプレッドシートの行データ
        """
        pass

    @abstractmethod
    def from_row(self, row: List[Any]) -> Dict[str, Any]:
        """スプレッドシートの行を辞書データに変換

        Args:
            row: スプレッドシートの行データ

        Returns:
            dict: エンティティデータ
        """
        pass

    def validate(self, data: Dict[str, Any]) -> None:
        """データを検証

        Args:
            data: 検証するデータ

        Raises:
            SheetsValidationError: 検証エラー
        """
        pass  # サブクラスでオーバーライド可能

    # ==========================================================================
    # CRUD操作
    # ==========================================================================

    def get_all(self) -> List[Dict[str, Any]]:
        """全レコードを取得

        Returns:
            list[dict]: 全レコードのリスト
        """
        values = self.client.get_all_values(self.worksheet)
        if len(values) <= 1:  # ヘッダーのみ
            return []

        records = []
        for row in values[1:]:  # ヘッダーをスキップ
            if any(row):  # 空行をスキップ
                try:
                    records.append(self.from_row(row))
                except Exception as e:
                    logger.warning(f"行の変換に失敗: {row}, エラー: {e}")
        return records

    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """IDでレコードを取得

        Args:
            record_id: レコードID

        Returns:
            dict or None: レコード（見つからない場合はNone）
        """
        row_number = self.client.find_row(self.worksheet, self.id_column, record_id)
        if not row_number:
            return None

        values = self.client.get_all_values(self.worksheet)
        if row_number > len(values):
            return None

        row = values[row_number - 1]
        return self.from_row(row)

    def find_by(self, column_name: str, value: Any) -> List[Dict[str, Any]]:
        """特定のカラム値でフィルタリング

        Args:
            column_name: カラム名
            value: 検索値

        Returns:
            list[dict]: マッチしたレコードのリスト
        """
        if column_name not in self.columns:
            raise SheetsValidationError(f"カラム '{column_name}' は存在しません")

        all_records = self.get_all()
        return [r for r in all_records if r.get(column_name) == value]

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """新規レコードを作成

        Args:
            data: 作成するデータ

        Returns:
            dict: 作成されたレコード（IDを含む）
        """
        self.validate(data)

        # IDを生成（既存でない場合）
        if 'id' not in data or not data['id']:
            data['id'] = str(uuid.uuid4())

        # タイムスタンプを設定
        now = timezone.now().isoformat()
        if 'created_at' not in data:
            data['created_at'] = now
        data['updated_at'] = now

        row = self.to_row(data)
        self.client.append_row(self.worksheet, row)

        logger.info(f"{self.sheet_name}にレコードを作成: {data.get('id')}")
        return data

    def update(self, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """レコードを更新

        Args:
            record_id: 更新するレコードのID
            data: 更新データ

        Returns:
            dict or None: 更新されたレコード（見つからない場合はNone）
        """
        row_number = self.client.find_row(self.worksheet, self.id_column, record_id)
        if not row_number:
            return None

        self.validate(data)

        # 既存データを取得してマージ
        existing = self.get_by_id(record_id)
        if existing:
            existing.update(data)
            data = existing

        data['id'] = record_id
        data['updated_at'] = timezone.now().isoformat()

        row = self.to_row(data)
        self.client.update_row(self.worksheet, row_number, row)

        logger.info(f"{self.sheet_name}のレコードを更新: {record_id}")
        return data

    def delete(self, record_id: str) -> bool:
        """レコードを削除

        Args:
            record_id: 削除するレコードのID

        Returns:
            bool: 削除成功の場合True
        """
        row_number = self.client.find_row(self.worksheet, self.id_column, record_id)
        if not row_number:
            return False

        self.client.delete_row(self.worksheet, row_number)
        logger.info(f"{self.sheet_name}のレコードを削除: {record_id}")
        return True

    def bulk_create(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """複数レコードを一括作成

        Args:
            records: 作成するデータのリスト

        Returns:
            list[dict]: 作成されたレコードのリスト
        """
        now = timezone.now().isoformat()
        rows = []
        created_records = []

        for data in records:
            self.validate(data)

            if 'id' not in data or not data['id']:
                data['id'] = str(uuid.uuid4())
            if 'created_at' not in data:
                data['created_at'] = now
            data['updated_at'] = now

            rows.append(self.to_row(data))
            created_records.append(data)

        if rows:
            self.client.append_rows(self.worksheet, rows)
            logger.info(f"{self.sheet_name}に{len(rows)}件のレコードを一括作成")

        return created_records

    def count(self) -> int:
        """レコード数を取得

        Returns:
            int: レコード数
        """
        values = self.client.get_all_values(self.worksheet)
        return max(0, len(values) - 1)  # ヘッダー行を除く

    def clear_all(self) -> None:
        """全レコードを削除（ヘッダーは保持）

        注意: この操作は取り消せません
        """
        self.client.clear_worksheet(self.worksheet)
        self._ensure_headers()
        logger.warning(f"{self.sheet_name}の全レコードを削除")

    # ==========================================================================
    # ユーティリティ
    # ==========================================================================

    def _parse_datetime(self, value: str) -> Optional[datetime]:
        """ISO形式の日時文字列をパース

        Args:
            value: 日時文字列

        Returns:
            datetime or None
        """
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None

    def _format_datetime(self, dt: datetime) -> str:
        """datetimeをISO形式文字列に変換

        Args:
            dt: datetime オブジェクト

        Returns:
            str: ISO形式文字列
        """
        if not dt:
            return ''
        return dt.isoformat()
