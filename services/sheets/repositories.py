"""Django ATS - Sheetsリポジトリ実装

各モデル用のスプレッドシートリポジトリ。
候補者、求人、応募、面接のCRUD操作を提供。
"""

from typing import Any, Dict, List, Optional

from .base_repository import BaseSheetsRepository
from .exceptions import SheetsValidationError


class CandidateRepository(BaseSheetsRepository):
    """候補者リポジトリ

    スプレッドシートの「候補者」シートを操作。
    """

    sheet_name = '候補者'
    columns = [
        'id',                    # A: UUID
        'name',                  # B: 氏名
        'name_kana',             # C: 氏名（かな）
        'email',                 # D: メールアドレス
        'phone',                 # E: 電話番号
        'birth_date',            # F: 生年月日
        'gender',                # G: 性別
        'postal_code',           # H: 郵便番号
        'address',               # I: 住所
        'current_company',       # J: 現在の勤務先
        'current_position',      # K: 現在の役職
        'years_of_experience',   # L: 経験年数
        'desired_salary_min',    # M: 希望年収（下限）
        'desired_salary_max',    # N: 希望年収（上限）
        'desired_job_types',     # O: 希望職種（カンマ区切り）
        'skills',                # P: スキル（カンマ区切り）
        'qualifications',        # Q: 資格（カンマ区切り）
        'education',             # R: 最終学歴
        'source',                # S: 流入経路
        'status',                # T: ステータス
        'notes',                 # U: 備考
        'registered_by_id',      # V: 登録者ID
        'created_at',            # W: 作成日時
        'updated_at',            # X: 更新日時
    ]
    id_column = 1

    def to_row(self, data: Dict[str, Any]) -> List[Any]:
        """辞書データを行に変換"""
        return [
            data.get('id', ''),
            data.get('name', ''),
            data.get('name_kana', ''),
            data.get('email', ''),
            data.get('phone', ''),
            data.get('birth_date', ''),
            data.get('gender', ''),
            data.get('postal_code', ''),
            data.get('address', ''),
            data.get('current_company', ''),
            data.get('current_position', ''),
            data.get('years_of_experience', ''),
            data.get('desired_salary_min', ''),
            data.get('desired_salary_max', ''),
            self._list_to_csv(data.get('desired_job_types', [])),
            self._list_to_csv(data.get('skills', [])),
            self._list_to_csv(data.get('qualifications', [])),
            data.get('education', ''),
            data.get('source', ''),
            data.get('status', 'new'),
            data.get('notes', ''),
            data.get('registered_by_id', ''),
            data.get('created_at', ''),
            data.get('updated_at', ''),
        ]

    def from_row(self, row: List[Any]) -> Dict[str, Any]:
        """行を辞書データに変換"""
        return {
            'id': self._get_value(row, 0),
            'name': self._get_value(row, 1),
            'name_kana': self._get_value(row, 2),
            'email': self._get_value(row, 3),
            'phone': self._get_value(row, 4),
            'birth_date': self._get_value(row, 5),
            'gender': self._get_value(row, 6),
            'postal_code': self._get_value(row, 7),
            'address': self._get_value(row, 8),
            'current_company': self._get_value(row, 9),
            'current_position': self._get_value(row, 10),
            'years_of_experience': self._parse_int(self._get_value(row, 11)),
            'desired_salary_min': self._parse_int(self._get_value(row, 12)),
            'desired_salary_max': self._parse_int(self._get_value(row, 13)),
            'desired_job_types': self._csv_to_list(self._get_value(row, 14)),
            'skills': self._csv_to_list(self._get_value(row, 15)),
            'qualifications': self._csv_to_list(self._get_value(row, 16)),
            'education': self._get_value(row, 17),
            'source': self._get_value(row, 18),
            'status': self._get_value(row, 19) or 'new',
            'notes': self._get_value(row, 20),
            'registered_by_id': self._get_value(row, 21),
            'created_at': self._get_value(row, 22),
            'updated_at': self._get_value(row, 23),
        }

    def validate(self, data: Dict[str, Any]) -> None:
        """データを検証"""
        if not data.get('name'):
            raise SheetsValidationError("氏名は必須です", field='name')
        if not data.get('email'):
            raise SheetsValidationError("メールアドレスは必須です", field='email')

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """メールアドレスで候補者を検索"""
        results = self.find_by('email', email)
        return results[0] if results else None

    def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """ステータスで候補者を検索"""
        return self.find_by('status', status)

    def _get_value(self, row: List, index: int, default: str = '') -> str:
        """行から値を安全に取得"""
        try:
            return str(row[index]) if index < len(row) and row[index] else default
        except (IndexError, TypeError):
            return default

    def _parse_int(self, value: str) -> Optional[int]:
        """文字列を整数に変換"""
        try:
            return int(value) if value else None
        except ValueError:
            return None

    def _list_to_csv(self, values: List[str]) -> str:
        """リストをカンマ区切り文字列に変換"""
        if isinstance(values, list):
            return ', '.join(str(v) for v in values if v)
        return str(values) if values else ''

    def _csv_to_list(self, value: str) -> List[str]:
        """カンマ区切り文字列をリストに変換"""
        if not value:
            return []
        return [v.strip() for v in value.split(',') if v.strip()]


class JobRepository(BaseSheetsRepository):
    """求人リポジトリ

    スプレッドシートの「求人」シートを操作。
    """

    sheet_name = '求人'
    columns = [
        'id',                    # A: UUID
        'title',                 # B: 求人タイトル
        'department',            # C: 部署
        'employment_type',       # D: 雇用形態
        'job_category',          # E: 職種カテゴリ
        'description',           # F: 仕事内容
        'requirements',          # G: 応募要件
        'preferred_skills',      # H: 歓迎スキル
        'salary_min',            # I: 給与（下限）
        'salary_max',            # J: 給与（上限）
        'work_location',         # K: 勤務地
        'work_hours',            # L: 勤務時間
        'benefits',              # M: 福利厚生
        'number_of_positions',   # N: 募集人数
        'status',                # O: ステータス
        'published_at',          # P: 公開日
        'deadline',              # Q: 応募締切
        'notes',                 # R: 備考
        'created_by_id',         # S: 作成者ID
        'created_at',            # T: 作成日時
        'updated_at',            # U: 更新日時
    ]
    id_column = 1

    def to_row(self, data: Dict[str, Any]) -> List[Any]:
        """辞書データを行に変換"""
        return [
            data.get('id', ''),
            data.get('title', ''),
            data.get('department', ''),
            data.get('employment_type', ''),
            data.get('job_category', ''),
            data.get('description', ''),
            data.get('requirements', ''),
            data.get('preferred_skills', ''),
            data.get('salary_min', ''),
            data.get('salary_max', ''),
            data.get('work_location', ''),
            data.get('work_hours', ''),
            data.get('benefits', ''),
            data.get('number_of_positions', ''),
            data.get('status', 'draft'),
            data.get('published_at', ''),
            data.get('deadline', ''),
            data.get('notes', ''),
            data.get('created_by_id', ''),
            data.get('created_at', ''),
            data.get('updated_at', ''),
        ]

    def from_row(self, row: List[Any]) -> Dict[str, Any]:
        """行を辞書データに変換"""
        return {
            'id': self._get_value(row, 0),
            'title': self._get_value(row, 1),
            'department': self._get_value(row, 2),
            'employment_type': self._get_value(row, 3),
            'job_category': self._get_value(row, 4),
            'description': self._get_value(row, 5),
            'requirements': self._get_value(row, 6),
            'preferred_skills': self._get_value(row, 7),
            'salary_min': self._parse_int(self._get_value(row, 8)),
            'salary_max': self._parse_int(self._get_value(row, 9)),
            'work_location': self._get_value(row, 10),
            'work_hours': self._get_value(row, 11),
            'benefits': self._get_value(row, 12),
            'number_of_positions': self._parse_int(self._get_value(row, 13)),
            'status': self._get_value(row, 14) or 'draft',
            'published_at': self._get_value(row, 15),
            'deadline': self._get_value(row, 16),
            'notes': self._get_value(row, 17),
            'created_by_id': self._get_value(row, 18),
            'created_at': self._get_value(row, 19),
            'updated_at': self._get_value(row, 20),
        }

    def validate(self, data: Dict[str, Any]) -> None:
        """データを検証"""
        if not data.get('title'):
            raise SheetsValidationError("求人タイトルは必須です", field='title')

    def find_active(self) -> List[Dict[str, Any]]:
        """公開中の求人を取得"""
        return self.find_by('status', 'published')

    def _get_value(self, row: List, index: int, default: str = '') -> str:
        try:
            return str(row[index]) if index < len(row) and row[index] else default
        except (IndexError, TypeError):
            return default

    def _parse_int(self, value: str) -> Optional[int]:
        try:
            return int(value) if value else None
        except ValueError:
            return None


class ApplicationRepository(BaseSheetsRepository):
    """応募リポジトリ

    スプレッドシートの「応募」シートを操作。
    """

    sheet_name = '応募'
    columns = [
        'id',                    # A: UUID
        'candidate_id',          # B: 候補者ID
        'candidate_name',        # C: 候補者名（表示用）
        'job_id',                # D: 求人ID
        'job_title',             # E: 求人タイトル（表示用）
        'status',                # F: ステータス
        'source',                # G: 応募経路
        'applied_at',            # H: 応募日時
        'evaluation_score',      # I: 評価スコア
        'evaluation_notes',      # J: 評価コメント
        'offer_salary',          # K: 提示年収
        'offer_made_at',         # L: 内定日
        'offer_deadline',        # M: 内定回答期限
        'offer_notes',           # N: 内定条件メモ
        'joined_at',             # O: 入社日
        'notes',                 # P: 備考
        'registered_by_id',      # Q: 登録者ID
        'created_at',            # R: 作成日時
        'updated_at',            # S: 更新日時
    ]
    id_column = 1

    def to_row(self, data: Dict[str, Any]) -> List[Any]:
        """辞書データを行に変換"""
        return [
            data.get('id', ''),
            data.get('candidate_id', ''),
            data.get('candidate_name', ''),
            data.get('job_id', ''),
            data.get('job_title', ''),
            data.get('status', 'new'),
            data.get('source', ''),
            data.get('applied_at', ''),
            data.get('evaluation_score', ''),
            data.get('evaluation_notes', ''),
            data.get('offer_salary', ''),
            data.get('offer_made_at', ''),
            data.get('offer_deadline', ''),
            data.get('offer_notes', ''),
            data.get('joined_at', ''),
            data.get('notes', ''),
            data.get('registered_by_id', ''),
            data.get('created_at', ''),
            data.get('updated_at', ''),
        ]

    def from_row(self, row: List[Any]) -> Dict[str, Any]:
        """行を辞書データに変換"""
        return {
            'id': self._get_value(row, 0),
            'candidate_id': self._get_value(row, 1),
            'candidate_name': self._get_value(row, 2),
            'job_id': self._get_value(row, 3),
            'job_title': self._get_value(row, 4),
            'status': self._get_value(row, 5) or 'new',
            'source': self._get_value(row, 6),
            'applied_at': self._get_value(row, 7),
            'evaluation_score': self._parse_int(self._get_value(row, 8)),
            'evaluation_notes': self._get_value(row, 9),
            'offer_salary': self._parse_int(self._get_value(row, 10)),
            'offer_made_at': self._get_value(row, 11),
            'offer_deadline': self._get_value(row, 12),
            'offer_notes': self._get_value(row, 13),
            'joined_at': self._get_value(row, 14),
            'notes': self._get_value(row, 15),
            'registered_by_id': self._get_value(row, 16),
            'created_at': self._get_value(row, 17),
            'updated_at': self._get_value(row, 18),
        }

    def validate(self, data: Dict[str, Any]) -> None:
        """データを検証"""
        if not data.get('candidate_id'):
            raise SheetsValidationError("候補者IDは必須です", field='candidate_id')
        if not data.get('job_id'):
            raise SheetsValidationError("求人IDは必須です", field='job_id')

    def find_by_candidate(self, candidate_id: str) -> List[Dict[str, Any]]:
        """候補者IDで応募を検索"""
        return self.find_by('candidate_id', candidate_id)

    def find_by_job(self, job_id: str) -> List[Dict[str, Any]]:
        """求人IDで応募を検索"""
        return self.find_by('job_id', job_id)

    def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """ステータスで応募を検索"""
        return self.find_by('status', status)

    def _get_value(self, row: List, index: int, default: str = '') -> str:
        try:
            return str(row[index]) if index < len(row) and row[index] else default
        except (IndexError, TypeError):
            return default

    def _parse_int(self, value: str) -> Optional[int]:
        try:
            return int(value) if value else None
        except ValueError:
            return None


class InterviewRepository(BaseSheetsRepository):
    """面接リポジトリ

    スプレッドシートの「面接」シートを操作。
    """

    sheet_name = '面接'
    columns = [
        'id',                    # A: UUID
        'application_id',        # B: 応募ID
        'candidate_name',        # C: 候補者名（表示用）
        'job_title',             # D: 求人タイトル（表示用）
        'interview_type',        # E: 面接種別
        'round_number',          # F: 面接回数
        'scheduled_at',          # G: 予定日時
        'duration_minutes',      # H: 所要時間（分）
        'location',              # I: 場所
        'meeting_url',           # J: オンラインURL
        'interviewer_ids',       # K: 面接官ID（カンマ区切り）
        'interviewer_names',     # L: 面接官名（カンマ区切り）
        'status',                # M: ステータス
        'result',                # N: 結果
        'feedback',              # O: フィードバック
        'score',                 # P: 評価スコア
        'notes',                 # Q: 備考
        'created_by_id',         # R: 作成者ID
        'created_at',            # S: 作成日時
        'updated_at',            # T: 更新日時
    ]
    id_column = 1

    def to_row(self, data: Dict[str, Any]) -> List[Any]:
        """辞書データを行に変換"""
        return [
            data.get('id', ''),
            data.get('application_id', ''),
            data.get('candidate_name', ''),
            data.get('job_title', ''),
            data.get('interview_type', ''),
            data.get('round_number', ''),
            data.get('scheduled_at', ''),
            data.get('duration_minutes', ''),
            data.get('location', ''),
            data.get('meeting_url', ''),
            self._list_to_csv(data.get('interviewer_ids', [])),
            self._list_to_csv(data.get('interviewer_names', [])),
            data.get('status', 'scheduled'),
            data.get('result', ''),
            data.get('feedback', ''),
            data.get('score', ''),
            data.get('notes', ''),
            data.get('created_by_id', ''),
            data.get('created_at', ''),
            data.get('updated_at', ''),
        ]

    def from_row(self, row: List[Any]) -> Dict[str, Any]:
        """行を辞書データに変換"""
        return {
            'id': self._get_value(row, 0),
            'application_id': self._get_value(row, 1),
            'candidate_name': self._get_value(row, 2),
            'job_title': self._get_value(row, 3),
            'interview_type': self._get_value(row, 4),
            'round_number': self._parse_int(self._get_value(row, 5)),
            'scheduled_at': self._get_value(row, 6),
            'duration_minutes': self._parse_int(self._get_value(row, 7)),
            'location': self._get_value(row, 8),
            'meeting_url': self._get_value(row, 9),
            'interviewer_ids': self._csv_to_list(self._get_value(row, 10)),
            'interviewer_names': self._csv_to_list(self._get_value(row, 11)),
            'status': self._get_value(row, 12) or 'scheduled',
            'result': self._get_value(row, 13),
            'feedback': self._get_value(row, 14),
            'score': self._parse_int(self._get_value(row, 15)),
            'notes': self._get_value(row, 16),
            'created_by_id': self._get_value(row, 17),
            'created_at': self._get_value(row, 18),
            'updated_at': self._get_value(row, 19),
        }

    def validate(self, data: Dict[str, Any]) -> None:
        """データを検証"""
        if not data.get('application_id'):
            raise SheetsValidationError("応募IDは必須です", field='application_id')

    def find_by_application(self, application_id: str) -> List[Dict[str, Any]]:
        """応募IDで面接を検索"""
        return self.find_by('application_id', application_id)

    def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """ステータスで面接を検索"""
        return self.find_by('status', status)

    def find_upcoming(self) -> List[Dict[str, Any]]:
        """予定されている面接を取得"""
        return self.find_by('status', 'scheduled')

    def _get_value(self, row: List, index: int, default: str = '') -> str:
        try:
            return str(row[index]) if index < len(row) and row[index] else default
        except (IndexError, TypeError):
            return default

    def _parse_int(self, value: str) -> Optional[int]:
        try:
            return int(value) if value else None
        except ValueError:
            return None

    def _list_to_csv(self, values: List[str]) -> str:
        if isinstance(values, list):
            return ', '.join(str(v) for v in values if v)
        return str(values) if values else ''

    def _csv_to_list(self, value: str) -> List[str]:
        if not value:
            return []
        return [v.strip() for v in value.split(',') if v.strip()]


# =============================================================================
# リポジトリファクトリ
# =============================================================================

class SheetsRepositoryFactory:
    """リポジトリファクトリ

    スプレッドシートIDを指定してリポジトリを取得。

    使用例:
        factory = SheetsRepositoryFactory(spreadsheet_id)
        candidates = factory.candidates.get_all()
        jobs = factory.jobs.find_active()
    """

    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self._candidates = None
        self._jobs = None
        self._applications = None
        self._interviews = None

    @property
    def candidates(self) -> CandidateRepository:
        """候補者リポジトリを取得"""
        if self._candidates is None:
            self._candidates = CandidateRepository(self.spreadsheet_id)
        return self._candidates

    @property
    def jobs(self) -> JobRepository:
        """求人リポジトリを取得"""
        if self._jobs is None:
            self._jobs = JobRepository(self.spreadsheet_id)
        return self._jobs

    @property
    def applications(self) -> ApplicationRepository:
        """応募リポジトリを取得"""
        if self._applications is None:
            self._applications = ApplicationRepository(self.spreadsheet_id)
        return self._applications

    @property
    def interviews(self) -> InterviewRepository:
        """面接リポジトリを取得"""
        if self._interviews is None:
            self._interviews = InterviewRepository(self.spreadsheet_id)
        return self._interviews
