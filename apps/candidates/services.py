"""
Django ATS - 候補者サービス

CSVインポート等のビジネスロジックを提供。
"""

import csv
import io
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from django.utils import timezone

from .models import Candidate, ImportHistory, GenderChoices, EmploymentStatusChoices


@dataclass
class CSVFieldMapping:
    """CSVフィールドマッピング"""
    csv_column: str
    model_field: str
    required: bool = False
    transform: callable = None


class CSVImportError(Exception):
    """CSVインポートエラー"""
    def __init__(self, message: str, row_number: int = None, field: str = None):
        self.message = message
        self.row_number = row_number
        self.field = field
        super().__init__(message)


class CandidateCSVImporter:
    """候補者CSVインポーター

    CSVファイルから候補者を一括インポート。

    使用例:
        importer = CandidateCSVImporter(tenant, user)
        result = importer.import_csv(csv_file)
    """

    # デフォルトのフィールドマッピング
    DEFAULT_FIELD_MAPPING = [
        CSVFieldMapping('氏名', 'name', required=True),
        CSVFieldMapping('氏名（カナ）', 'name_kana'),
        CSVFieldMapping('メールアドレス', 'email', required=True),
        CSVFieldMapping('電話番号', 'phone'),
        CSVFieldMapping('性別', 'gender', transform=lambda x: GenderChoices.MALE if x == '男性' else (GenderChoices.FEMALE if x == '女性' else GenderChoices.UNSPECIFIED)),
        CSVFieldMapping('生年月日', 'birth_date'),
        CSVFieldMapping('住所', 'address'),
        CSVFieldMapping('現職企業', 'current_company'),
        CSVFieldMapping('現職役職', 'current_position'),
        CSVFieldMapping('就業状況', 'employment_status', transform=lambda x: EmploymentStatusChoices.EMPLOYED if x == '就業中' else (EmploymentStatusChoices.UNEMPLOYED if x == '離職中' else EmploymentStatusChoices.EMPLOYED)),
        CSVFieldMapping('経験年数', 'years_of_experience', transform=lambda x: int(x) if x.isdigit() else None),
        CSVFieldMapping('希望年収', 'desired_salary', transform=lambda x: int(x) if x.isdigit() else None),
        CSVFieldMapping('スキル', 'skills', transform=lambda x: [s.strip() for s in x.split(',') if s.strip()]),
        CSVFieldMapping('資格', 'qualifications', transform=lambda x: [s.strip() for s in x.split(',') if s.strip()]),
        CSVFieldMapping('最終学歴', 'education'),
        CSVFieldMapping('履歴書URL', 'resume_url'),
        CSVFieldMapping('職務経歴書URL', 'cv_url'),
        CSVFieldMapping('備考', 'notes'),
    ]

    # 英語ヘッダーのマッピング
    ENGLISH_FIELD_MAPPING = [
        CSVFieldMapping('name', 'name', required=True),
        CSVFieldMapping('name_kana', 'name_kana'),
        CSVFieldMapping('email', 'email', required=True),
        CSVFieldMapping('phone', 'phone'),
        CSVFieldMapping('gender', 'gender'),
        CSVFieldMapping('birth_date', 'birth_date'),
        CSVFieldMapping('address', 'address'),
        CSVFieldMapping('current_company', 'current_company'),
        CSVFieldMapping('current_position', 'current_position'),
        CSVFieldMapping('employment_status', 'employment_status'),
        CSVFieldMapping('years_of_experience', 'years_of_experience', transform=lambda x: int(x) if x.isdigit() else None),
        CSVFieldMapping('desired_salary', 'desired_salary', transform=lambda x: int(x) if x.isdigit() else None),
        CSVFieldMapping('skills', 'skills', transform=lambda x: [s.strip() for s in x.split(',') if s.strip()]),
        CSVFieldMapping('qualifications', 'qualifications', transform=lambda x: [s.strip() for s in x.split(',') if s.strip()]),
        CSVFieldMapping('education', 'education'),
        CSVFieldMapping('resume_url', 'resume_url'),
        CSVFieldMapping('cv_url', 'cv_url'),
        CSVFieldMapping('notes', 'notes'),
    ]

    def __init__(self, tenant, user, field_mapping=None):
        """
        Args:
            tenant: テナント
            user: インポート実行ユーザー
            field_mapping: カスタムフィールドマッピング（オプション）
        """
        self.tenant = tenant
        self.user = user
        self.field_mapping = field_mapping

    def import_csv(
        self,
        csv_file,
        encoding: str = 'utf-8',
        skip_duplicates: bool = True,
        dry_run: bool = False
    ) -> ImportHistory:
        """CSVファイルから候補者をインポート

        Args:
            csv_file: CSVファイルオブジェクト
            encoding: ファイルエンコーディング
            skip_duplicates: 重複をスキップするか
            dry_run: テスト実行（DBに保存しない）

        Returns:
            ImportHistory: インポート履歴
        """
        # インポート履歴を作成
        history = ImportHistory.objects.create(
            tenant=self.tenant,
            file_name=getattr(csv_file, 'name', 'unknown.csv'),
            status=ImportHistory.StatusChoices.PROCESSING,
            created_by=self.user,
            started_at=timezone.now()
        )

        try:
            # CSVを読み込み
            content = csv_file.read()
            if isinstance(content, bytes):
                content = content.decode(encoding)

            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
            history.total_rows = len(rows)
            history.save()

            # フィールドマッピングを決定
            if not self.field_mapping:
                self.field_mapping = self._detect_field_mapping(reader.fieldnames)

            # 各行を処理
            success_count = 0
            error_count = 0
            error_log = []

            for row_number, row in enumerate(rows, start=2):  # ヘッダー行があるので2から開始
                try:
                    candidate_data = self._parse_row(row, row_number)

                    # 重複チェック
                    if skip_duplicates and self._is_duplicate(candidate_data['email']):
                        error_log.append({
                            'row': row_number,
                            'error': f"メールアドレス '{candidate_data['email']}' は既に登録されています",
                            'skipped': True
                        })
                        continue

                    # 候補者を作成
                    if not dry_run:
                        self._create_candidate(candidate_data)

                    success_count += 1

                except CSVImportError as e:
                    error_count += 1
                    error_log.append({
                        'row': e.row_number or row_number,
                        'field': e.field,
                        'error': e.message
                    })
                except Exception as e:
                    error_count += 1
                    error_log.append({
                        'row': row_number,
                        'error': str(e)
                    })

            # 履歴を更新
            history.success_count = success_count
            history.error_count = error_count
            history.error_log = error_log
            history.completed_at = timezone.now()

            if error_count == 0:
                history.status = ImportHistory.StatusChoices.COMPLETED
            elif success_count == 0:
                history.status = ImportHistory.StatusChoices.FAILED
            else:
                history.status = ImportHistory.StatusChoices.PARTIAL

            history.save()
            return history

        except Exception as e:
            history.status = ImportHistory.StatusChoices.FAILED
            history.error_log = [{'error': str(e)}]
            history.completed_at = timezone.now()
            history.save()
            raise

    def _detect_field_mapping(self, fieldnames: List[str]) -> List[CSVFieldMapping]:
        """ヘッダーからフィールドマッピングを検出"""
        if not fieldnames:
            return self.DEFAULT_FIELD_MAPPING

        # 日本語ヘッダーか英語ヘッダーかを判定
        japanese_headers = {'氏名', 'メールアドレス', '電話番号'}
        if any(h in fieldnames for h in japanese_headers):
            return self.DEFAULT_FIELD_MAPPING
        else:
            return self.ENGLISH_FIELD_MAPPING

    def _parse_row(self, row: Dict[str, str], row_number: int) -> Dict[str, Any]:
        """行をパースして候補者データに変換"""
        data = {}

        for mapping in self.field_mapping:
            value = row.get(mapping.csv_column, '').strip()

            if mapping.required and not value:
                raise CSVImportError(
                    f"必須項目 '{mapping.csv_column}' が空です",
                    row_number=row_number,
                    field=mapping.csv_column
                )

            if value and mapping.transform:
                try:
                    value = mapping.transform(value)
                except Exception as e:
                    raise CSVImportError(
                        f"'{mapping.csv_column}' の変換に失敗: {str(e)}",
                        row_number=row_number,
                        field=mapping.csv_column
                    )

            if value:  # 空でない場合のみ設定
                data[mapping.model_field] = value

        return data

    def _is_duplicate(self, email: str) -> bool:
        """重複チェック"""
        return Candidate.objects.filter(
            tenant=self.tenant,
            email=email
        ).exists()

    def _create_candidate(self, data: Dict[str, Any]) -> Candidate:
        """候補者を作成"""
        return Candidate.objects.create(
            tenant=self.tenant,
            registered_by=self.user,
            **data
        )

    def validate_csv(self, csv_file, encoding: str = 'utf-8') -> Tuple[bool, List[Dict]]:
        """CSVファイルを検証（インポートせずにエラーをチェック）

        Args:
            csv_file: CSVファイルオブジェクト
            encoding: ファイルエンコーディング

        Returns:
            Tuple[bool, List[Dict]]: (有効かどうか, エラーリスト)
        """
        errors = []

        try:
            content = csv_file.read()
            if isinstance(content, bytes):
                content = content.decode(encoding)

            # ファイルポインタをリセット
            csv_file.seek(0)

            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)

            if not rows:
                errors.append({'error': 'CSVファイルにデータがありません'})
                return False, errors

            # フィールドマッピングを決定
            if not self.field_mapping:
                self.field_mapping = self._detect_field_mapping(reader.fieldnames)

            # 必須フィールドの存在確認
            required_columns = [m.csv_column for m in self.field_mapping if m.required]
            missing_columns = [c for c in required_columns if c not in reader.fieldnames]
            if missing_columns:
                errors.append({
                    'error': f"必須列が見つかりません: {', '.join(missing_columns)}"
                })

            # 各行を検証
            for row_number, row in enumerate(rows, start=2):
                try:
                    self._parse_row(row, row_number)
                except CSVImportError as e:
                    errors.append({
                        'row': e.row_number,
                        'field': e.field,
                        'error': e.message
                    })

            return len(errors) == 0, errors

        except Exception as e:
            errors.append({'error': f'CSVファイルの読み込みに失敗: {str(e)}'})
            return False, errors

    @staticmethod
    def generate_template_csv() -> str:
        """テンプレートCSVを生成"""
        headers = [
            '氏名', '氏名（カナ）', 'メールアドレス', '電話番号',
            '性別', '生年月日', '住所',
            '現職企業', '現職役職', '就業状況', '経験年数',
            '希望年収', 'スキル', '資格', '最終学歴',
            '履歴書URL', '職務経歴書URL', '備考'
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)

        # サンプルデータ
        writer.writerow([
            '山田太郎', 'ヤマダタロウ', 'yamada@example.com', '090-1234-5678',
            '男性', '1990-01-01', '東京都渋谷区...',
            '株式会社ABC', '営業部長', '就業中', '10',
            '600', 'Python, JavaScript', '基本情報技術者', '○○大学 工学部卒',
            '', '', '転職理由：キャリアアップ'
        ])

        return output.getvalue()
