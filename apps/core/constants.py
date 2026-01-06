"""Django ATS - 定数定義

アプリケーション全体で使用される定数を一元管理。
"""


class SyncDirection:
    """同期方向の定義

    データフローの方向を明示的に定義することで、
    各エンティティの同期挙動を明確にする。
    """
    PUSH = 'push'  # DB → Spreadsheet
    PULL = 'pull'  # Spreadsheet → DB


class SyncPolicy:
    """エンティティ別同期ポリシー

    各エンティティのデータソースと同期方向を定義。

    データソース設計方針:
    - Master: PostgreSQL（常に正）
    - Replica: Google Spreadsheet（読み取り用ビュー）
    - 原則: DB → Spreadsheet（push）
    - 例外: ユーザー一括登録時のみ Spreadsheet → DB（pull）
    """
    # 候補者: DBが正、Spreadsheetは閲覧用
    CANDIDATES = SyncDirection.PUSH

    # 求人: DBが正、Spreadsheetは閲覧用
    JOBS = SyncDirection.PUSH

    # 応募: DBが正、Spreadsheetは閲覧用
    APPLICATIONS = SyncDirection.PUSH

    # 面接: DBが正、Spreadsheetは閲覧用
    INTERVIEWS = SyncDirection.PUSH

    # ユーザー: 双方向（スプレッドシートからの一括登録あり）
    USERS = 'bidirectional'


class DataSourcePriority:
    """データソース優先順位

    競合発生時、どちらのデータを優先するかを定義。
    """
    # DBを常に正とする（Single Source of Truth）
    MASTER = 'database'
    REPLICA = 'spreadsheet'

    # 競合解決ポリシー
    CONFLICT_RESOLUTION = MASTER  # 競合時はDBを優先


class Pagination:
    """ページネーション設定"""
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    CHOICES = [10, 20, 50, 100]


class SyncLimits:
    """同期処理の制限値"""
    MAX_ROWS_PER_BATCH = 1000
    API_RATE_LIMIT = 100  # requests per 100 seconds（Google Sheets API制限）
    RETRY_COUNT = 3
    RETRY_DELAY_SECONDS = 1.0


class EntityTypes:
    """エンティティタイプ定義"""
    CANDIDATES = 'candidates'
    JOBS = 'jobs'
    APPLICATIONS = 'applications'
    INTERVIEWS = 'interviews'
    USERS = 'users'

    ALL = [CANDIDATES, JOBS, APPLICATIONS, INTERVIEWS, USERS]
    BUSINESS = [CANDIDATES, JOBS, APPLICATIONS, INTERVIEWS]
    ADMIN = [USERS]


class SheetNames:
    """スプレッドシートのシート名（日本語）"""
    CANDIDATES = '候補者'
    JOBS = '求人'
    APPLICATIONS = '応募'
    INTERVIEWS = '面接'
    USERS = 'ユーザー'
    SETTINGS = '設定'

    # マッピング: 日本語 → 英語
    TO_ENTITY = {
        '候補者': EntityTypes.CANDIDATES,
        '求人': EntityTypes.JOBS,
        '応募': EntityTypes.APPLICATIONS,
        '面接': EntityTypes.INTERVIEWS,
        'ユーザー': EntityTypes.USERS,
    }

    # マッピング: 英語 → 日本語
    TO_JAPANESE = {
        EntityTypes.CANDIDATES: '候補者',
        EntityTypes.JOBS: '求人',
        EntityTypes.APPLICATIONS: '応募',
        EntityTypes.INTERVIEWS: '面接',
        EntityTypes.USERS: 'ユーザー',
    }


class SyncStatus:
    """同期ステータス"""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    SUCCESS = 'success'
    PARTIAL = 'partial'  # 一部成功
    FAILED = 'failed'


class ConflictAction:
    """競合解決アクション"""
    USE_DB = 'use_db'           # DBの値を使用
    USE_SHEET = 'use_sheet'     # シートの値を使用
    MERGE = 'merge'             # マージ（フィールド単位で新しい方を採用）
    SKIP = 'skip'               # スキップ（変更しない）
    MANUAL = 'manual'           # 手動解決が必要


# バリデーション用の正規表現パターン
class ValidationPatterns:
    """バリデーション用正規表現"""
    PHONE_NUMBER = r'^[\d\-\+\(\)\s]+$'
    POSTAL_CODE = r'^\d{3}-?\d{4}$'
    EMAIL = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'


# デフォルト値
class Defaults:
    """デフォルト値"""
    INTERVIEW_DURATION_MINUTES = 60
    JOB_HEADCOUNT = 1
    SYNC_INTERVAL_MINUTES = 5
