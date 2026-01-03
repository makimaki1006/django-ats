"""
スプレッドシート双方向同期サービス

Google Spreadsheetとの双方向同期を管理。

機能:
- アプリ → スプレッドシート: モデル変更時に自動反映
- スプレッドシート → アプリ: 手動または定期的に取り込み
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class SpreadsheetSyncService:
    """スプレッドシート同期サービス

    双方向同期を実現するためのサービスクラス。

    使用方法:
        # 接続テスト
        service = SpreadsheetSyncService(connection)
        if service.test_connection():
            print("接続成功")

        # アプリ → スプレッドシート
        service.push_to_spreadsheet('candidates')

        # スプレッドシート → アプリ
        service.pull_from_spreadsheet('candidates')

        # 全データ同期
        service.sync_all()
    """

    # シート名のマッピング（日本語 → 英語モデル名）
    SHEET_MAPPING = {
        '候補者': 'candidates',
        '求人': 'jobs',
        '応募': 'applications',
        '面接': 'interviews',
        '設定': 'settings',
    }

    # カラムマッピング（スプレッドシート → モデルフィールド）
    CANDIDATE_COLUMNS = {
        'id': 'id',
        'name': 'name',
        'name_kana': 'name_kana',
        'email': 'email',
        'phone': 'phone',
        'birth_date': 'birth_date',
        'gender': 'gender',
        'address': 'address',
        'current_company': 'current_company',
        'current_position': 'current_position',
        'employment_status': 'employment_status',
        'years_of_experience': 'years_of_experience',
        'desired_salary': 'desired_salary',
        'desired_positions': 'desired_positions',
        'desired_locations': 'desired_locations',
        'skills': 'skills',
        'qualifications': 'qualifications',
        'education': 'education',
        'notes': 'notes',
    }

    JOB_COLUMNS = {
        'id': 'id',
        'unique_code': 'unique_code',
        'title': 'title',
        'department': 'department',
        'team': 'team',
        'employment_type': 'employment_type',
        'location': 'location',
        'remote_policy': 'remote_policy',
        'salary_min': 'salary_min',
        'salary_max': 'salary_max',
        'description': 'description',
        'requirements': 'requirements',
        'preferred_requirements': 'preferred_requirements',
        'benefits': 'benefits',
        'headcount': 'headcount',
        'status': 'status',
    }

    APPLICATION_COLUMNS = {
        'id': 'id',
        'candidate_id': 'candidate_id',
        'candidate_name': None,  # 表示用（同期しない）
        'job_id': 'job_id',
        'job_title': None,  # 表示用（同期しない）
        'status': 'status',
        'source': 'source',
        'applied_at': 'applied_at',
        'evaluation_score': 'evaluation_score',
        'evaluation_notes': 'evaluation_notes',
        'notes': 'notes',
    }

    INTERVIEW_COLUMNS = {
        'id': 'id',
        'application_id': 'application_id',
        'candidate_name': None,  # 表示用
        'job_title': None,  # 表示用
        'interview_type': 'interview_type',
        'interview_round': 'interview_round',
        'scheduled_at': 'scheduled_at',
        'duration_minutes': 'duration_minutes',
        'location': 'location',
        'status': 'status',
        'result': 'result',
        'feedback': 'feedback',
        'evaluation_score': 'evaluation_score',
        'internal_notes': 'internal_notes',
    }

    def __init__(self, connection):
        """
        Args:
            connection: SpreadsheetConnection インスタンス
        """
        self.connection = connection
        self.tenant = connection.tenant
        self._client = None
        self._spreadsheet = None

    def _get_client(self):
        """gspread クライアントを取得（遅延初期化）"""
        if self._client is None:
            try:
                import gspread
                from google.oauth2.service_account import Credentials

                credentials_data = json.loads(self.connection.credentials_json)
                scopes = [
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive.readonly',
                ]
                credentials = Credentials.from_service_account_info(
                    credentials_data,
                    scopes=scopes
                )
                self._client = gspread.authorize(credentials)
            except ImportError:
                raise ImportError("gspread と google-auth がインストールされていません。"
                                  "pip install gspread google-auth を実行してください。")
            except Exception as e:
                logger.error(f"Google認証エラー: {e}")
                raise

        return self._client

    def _get_spreadsheet(self):
        """スプレッドシートを取得"""
        if self._spreadsheet is None:
            client = self._get_client()
            self._spreadsheet = client.open_by_key(self.connection.spreadsheet_id)
        return self._spreadsheet

    def _get_worksheet(self, sheet_name: str):
        """ワークシートを取得（存在しなければ作成）"""
        spreadsheet = self._get_spreadsheet()
        try:
            return spreadsheet.worksheet(sheet_name)
        except Exception:
            # シートが存在しない場合は作成
            return spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=30)

    def test_connection(self) -> Tuple[bool, str]:
        """接続テスト

        Returns:
            (成功フラグ, メッセージ)
        """
        try:
            spreadsheet = self._get_spreadsheet()
            title = spreadsheet.title
            self.connection.spreadsheet_name = title
            # spreadsheet_nameを先に保存（mark_syncedはupdate_fieldsを使うため）
            self.connection.save(update_fields=['spreadsheet_name', 'updated_at'])
            self.connection.mark_synced()
            return True, f"接続成功: {title}"
        except Exception as e:
            error_msg = str(e)
            self.connection.mark_error(error_msg)
            logger.error(f"接続テスト失敗: {error_msg}")
            return False, f"接続失敗: {error_msg}"

    # =========================================================================
    # アプリ → スプレッドシート（Push）
    # =========================================================================

    def push_candidates(self) -> int:
        """候補者データをスプレッドシートに反映"""
        import json
        from apps.candidates.models import Candidate

        worksheet = self._get_worksheet('候補者')
        candidates = Candidate.objects.filter(tenant=self.tenant)

        # ヘッダー行
        headers = list(self.CANDIDATE_COLUMNS.keys()) + ['created_at', 'updated_at']

        # データ行
        rows = [headers]
        for c in candidates:
            row = [
                str(c.id),
                c.name or '',
                c.name_kana or '',
                c.email or '',
                c.phone or '',
                c.birth_date.isoformat() if c.birth_date else '',
                c.gender or '',
                c.address or '',
                c.current_company or '',
                c.current_position or '',
                c.employment_status or '',
                str(c.years_of_experience) if c.years_of_experience else '',
                str(c.desired_salary) if c.desired_salary else '',
                json.dumps(c.desired_positions, ensure_ascii=False) if c.desired_positions else '',
                json.dumps(c.desired_locations, ensure_ascii=False) if c.desired_locations else '',
                json.dumps(c.skills, ensure_ascii=False) if c.skills else '',
                json.dumps(c.qualifications, ensure_ascii=False) if c.qualifications else '',
                c.education or '',
                c.notes or '',
                c.created_at.isoformat() if c.created_at else '',
                c.updated_at.isoformat() if c.updated_at else '',
            ]
            rows.append(row)

        # シートをクリアして書き込み
        worksheet.clear()
        worksheet.update(rows, 'A1')

        return len(rows) - 1  # ヘッダー除く

    def push_jobs(self) -> int:
        """求人データをスプレッドシートに反映"""
        from apps.jobs.models import Job

        worksheet = self._get_worksheet('求人')
        jobs = Job.objects.filter(tenant=self.tenant)

        headers = list(self.JOB_COLUMNS.keys()) + ['created_at', 'updated_at']

        rows = [headers]
        for j in jobs:
            row = [
                str(j.id),
                j.unique_code or '',
                j.title or '',
                j.department or '',
                j.team or '',
                j.employment_type or '',
                j.location or '',
                j.remote_policy or '',
                str(j.salary_min) if j.salary_min else '',
                str(j.salary_max) if j.salary_max else '',
                j.description or '',
                j.requirements or '',
                j.preferred_requirements or '',
                j.benefits or '',
                str(j.headcount) if j.headcount else '',
                j.status or '',
                j.created_at.isoformat() if j.created_at else '',
                j.updated_at.isoformat() if j.updated_at else '',
            ]
            rows.append(row)

        worksheet.clear()
        worksheet.update(rows, 'A1')

        return len(rows) - 1

    def push_applications(self) -> int:
        """応募データをスプレッドシートに反映"""
        from apps.applications.models import Application

        worksheet = self._get_worksheet('応募')
        applications = Application.objects.filter(
            candidate__tenant=self.tenant
        ).select_related('candidate', 'job', 'source')

        headers = list(self.APPLICATION_COLUMNS.keys()) + ['created_at', 'updated_at']

        rows = [headers]
        for a in applications:
            row = [
                str(a.id),
                str(a.candidate_id) if a.candidate else '',
                a.candidate.name if a.candidate else '',
                str(a.job_id) if a.job else '',
                a.job.title if a.job else '',
                a.status or '',
                a.source.name if a.source else '',
                a.applied_at.isoformat() if a.applied_at else '',
                str(a.evaluation_score) if a.evaluation_score else '',
                a.evaluation_notes or '',
                a.notes or '',
                a.created_at.isoformat() if a.created_at else '',
                a.updated_at.isoformat() if a.updated_at else '',
            ]
            rows.append(row)

        worksheet.clear()
        worksheet.update(rows, 'A1')

        return len(rows) - 1

    def push_interviews(self) -> int:
        """面接データをスプレッドシートに反映"""
        from apps.interviews.models import Interview

        worksheet = self._get_worksheet('面接')
        interviews = Interview.objects.filter(
            application__candidate__tenant=self.tenant
        ).select_related('application__candidate', 'application__job')

        headers = list(self.INTERVIEW_COLUMNS.keys()) + ['created_at', 'updated_at']

        rows = [headers]
        for i in interviews:
            row = [
                str(i.id),
                str(i.application_id) if i.application else '',
                i.application.candidate.name if i.application and i.application.candidate else '',
                i.application.job.title if i.application and i.application.job else '',
                i.interview_type or '',
                str(i.interview_round) if i.interview_round else '',
                i.scheduled_at.isoformat() if i.scheduled_at else '',
                str(i.duration_minutes) if i.duration_minutes else '',
                i.location or '',
                i.status or '',
                i.result or '',
                i.feedback or '',
                str(i.evaluation_score) if i.evaluation_score else '',
                i.internal_notes or '',
                i.created_at.isoformat() if i.created_at else '',
                i.updated_at.isoformat() if i.updated_at else '',
            ]
            rows.append(row)

        worksheet.clear()
        worksheet.update(rows, 'A1')

        return len(rows) - 1

    def push_to_spreadsheet(self, model_type: str = None) -> Dict[str, int]:
        """アプリデータをスプレッドシートに反映

        Args:
            model_type: 'candidates', 'jobs', 'applications', 'interviews' or None（全て）

        Returns:
            各モデルの同期件数
        """
        self.connection.mark_syncing()
        results = {}

        try:
            if model_type is None or model_type == 'candidates':
                if self.connection.sync_candidates:
                    results['candidates'] = self.push_candidates()

            if model_type is None or model_type == 'jobs':
                if self.connection.sync_jobs:
                    results['jobs'] = self.push_jobs()

            if model_type is None or model_type == 'applications':
                if self.connection.sync_applications:
                    results['applications'] = self.push_applications()

            if model_type is None or model_type == 'interviews':
                if self.connection.sync_interviews:
                    results['interviews'] = self.push_interviews()

            self.connection.mark_synced()
            logger.info(f"Push完了: {results}")

        except Exception as e:
            self.connection.mark_error(str(e))
            logger.error(f"Push失敗: {e}")
            raise

        return results

    # =========================================================================
    # スプレッドシート → アプリ（Pull）
    # =========================================================================

    def _parse_date(self, value: str) -> Optional[datetime]:
        """日付文字列をパース"""
        if not value:
            return None
        try:
            # ISO 8601形式
            if 'T' in value:
                value = value.replace('+09:00', '+0900')
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            # YYYY-MM-DD形式
            return datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return None

    def _parse_int(self, value: str) -> Optional[int]:
        """整数文字列をパース"""
        if not value:
            return None
        try:
            return int(float(value))
        except ValueError:
            return None

    def pull_candidates(self) -> Tuple[int, int, int]:
        """スプレッドシートから候補者データを取り込み

        Returns:
            (作成件数, 更新件数, スキップ件数)
        """
        from apps.candidates.models import Candidate

        worksheet = self._get_worksheet('候補者')
        records = worksheet.get_all_records()

        created = updated = skipped = 0

        with transaction.atomic():
            for record in records:
                email = record.get('email', '')

                if not email:
                    skipped += 1
                    continue

                # メールで既存レコードを検索
                # JSONフィールドのパース
                skills_raw = record.get('skills', '')
                skills = skills_raw.split(',') if skills_raw else []

                qualifications_raw = record.get('qualifications', '')
                qualifications = qualifications_raw.split(',') if qualifications_raw else []

                desired_positions_raw = record.get('desired_positions', '') or record.get('desired_job_types', '')
                desired_positions = desired_positions_raw.split(',') if desired_positions_raw else []

                # genderのデフォルト値
                from apps.candidates.models import GenderChoices
                gender = record.get('gender', '') or GenderChoices.UNSPECIFIED

                candidate, is_created = Candidate.objects.update_or_create(
                    tenant=self.tenant,
                    email=email,
                    defaults={
                        'name': record.get('name', ''),
                        'name_kana': record.get('name_kana', ''),
                        'phone': record.get('phone', ''),
                        'birth_date': self._parse_date(record.get('birth_date', '')),
                        'gender': gender,
                        'address': record.get('address', ''),
                        'current_company': record.get('current_company', ''),
                        'current_position': record.get('current_position', ''),
                        'years_of_experience': self._parse_int(record.get('years_of_experience', '')),
                        'desired_salary': self._parse_int(record.get('desired_salary', '')),
                        'desired_positions': desired_positions,
                        'skills': skills,
                        'qualifications': qualifications,
                        'education': record.get('education', ''),
                        'notes': record.get('notes', ''),
                    }
                )

                if is_created:
                    created += 1
                else:
                    updated += 1

        return created, updated, skipped

    def pull_jobs(self) -> Tuple[int, int, int]:
        """スプレッドシートから求人データを取り込み"""
        from apps.jobs.models import Job

        worksheet = self._get_worksheet('求人')
        records = worksheet.get_all_records()

        created = updated = skipped = 0

        with transaction.atomic():
            for record in records:
                title = record.get('title', '')

                if not title:
                    skipped += 1
                    continue

                # タイトルで既存レコードを検索（または unique_code）
                unique_code = record.get('id', '')[:20] if record.get('id') else None

                job, is_created = Job.objects.update_or_create(
                    tenant=self.tenant,
                    unique_code=unique_code or title[:20],
                    defaults={
                        'title': title,
                        'department': record.get('department', ''),
                        'employment_type': record.get('employment_type', 'full_time'),
                        'job_category': record.get('job_category', ''),
                        'description': record.get('description', ''),
                        'requirements': record.get('requirements', ''),
                        'preferred_requirements': record.get('preferred_skills', ''),
                        'salary_min': self._parse_int(record.get('salary_min', '')),
                        'salary_max': self._parse_int(record.get('salary_max', '')),
                        'location': record.get('work_location', ''),
                        'work_hours': record.get('work_hours', ''),
                        'benefits': record.get('benefits', ''),
                        'headcount': self._parse_int(record.get('number_of_positions', '')) or 1,
                        'status': record.get('status', 'draft'),
                        'notes': record.get('notes', ''),
                    }
                )

                if is_created:
                    created += 1
                else:
                    updated += 1

        return created, updated, skipped

    def pull_from_spreadsheet(self, model_type: str = None) -> Dict[str, Tuple[int, int, int]]:
        """スプレッドシートからデータを取り込み

        Args:
            model_type: 'candidates', 'jobs' or None（全て）

        Returns:
            各モデルの (作成件数, 更新件数, スキップ件数)
        """
        self.connection.mark_syncing()
        results = {}

        try:
            if model_type is None or model_type == 'candidates':
                if self.connection.sync_candidates:
                    results['candidates'] = self.pull_candidates()

            if model_type is None or model_type == 'jobs':
                if self.connection.sync_jobs:
                    results['jobs'] = self.pull_jobs()

            # 応募・面接は依存関係があるため、候補者・求人の後に処理
            # （実装省略 - 必要に応じて追加）

            self.connection.mark_synced()
            logger.info(f"Pull完了: {results}")

        except Exception as e:
            self.connection.mark_error(str(e))
            logger.error(f"Pull失敗: {e}")
            raise

        return results

    # =========================================================================
    # 双方向同期
    # =========================================================================

    def sync_all(self) -> Dict[str, Any]:
        """全データの双方向同期

        Returns:
            同期結果サマリー
        """
        results = {
            'push': {},
            'pull': {},
            'timestamp': timezone.now().isoformat(),
        }

        # 1. まずスプレッドシートからPull（最新データを取得）
        results['pull'] = self.pull_from_spreadsheet()

        # 2. その後アプリからPush（マージ結果を反映）
        results['push'] = self.push_to_spreadsheet()

        return results

    def push_single_record(self, model_type: str, instance) -> bool:
        """単一レコードをスプレッドシートに反映（Signal用）

        Args:
            model_type: 'candidates', 'jobs', etc.
            instance: モデルインスタンス

        Returns:
            成功フラグ
        """
        if not self.connection.auto_sync_enabled:
            return False

        try:
            # シート全体を更新（効率的な差分更新は将来実装）
            self.push_to_spreadsheet(model_type)
            return True
        except Exception as e:
            logger.error(f"単一レコード同期失敗: {e}")
            return False
