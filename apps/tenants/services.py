"""Django ATS - テナントサービス

スプレッドシート同期など、テナント関連のビジネスロジック。

設計ポイント:
- Google Sheets APIを使用してデータを同期
- エラーハンドリングと再試行ロジック
- 同期履歴の記録
"""

import logging
from datetime import datetime
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class SpreadsheetSyncError(Exception):
    """スプレッドシート同期エラー"""
    pass


class SpreadsheetSyncService:
    """スプレッドシート同期サービス

    Google Spreadsheetとのデータ同期を管理。

    Usage:
        service = SpreadsheetSyncService(tenant_spreadsheet)
        service.sync_candidates()
        service.sync_applications()
    """

    # シート名の定義
    SHEET_CANDIDATES = '候補者一覧'
    SHEET_APPLICATIONS = '応募一覧'
    SHEET_INTERVIEWS = '面接一覧'
    SHEET_JOBS = '求人一覧'
    SHEET_SUMMARY = 'サマリー'

    # カラム定義
    CANDIDATE_COLUMNS = [
        'ID', '氏名', 'フリガナ', 'メール', '電話番号',
        '現在の会社', '現在の職種', '年齢', '性別',
        '就業状況', '登録日', '更新日'
    ]

    APPLICATION_COLUMNS = [
        'ID', '候補者名', '求人タイトル', 'ステータス',
        '応募日', '応募経路', 'エージェント', '更新日'
    ]

    INTERVIEW_COLUMNS = [
        'ID', '候補者名', '求人タイトル', '面接種別',
        '面接日時', '面接官', 'ステータス', '結果', '更新日'
    ]

    JOB_COLUMNS = [
        'ID', 'タイトル', '部署', '雇用形態', 'ステータス',
        '募集人数', '応募数', '公開日', '締切日'
    ]

    def __init__(self, tenant_spreadsheet):
        """初期化

        Args:
            tenant_spreadsheet: TenantSpreadsheetインスタンス
        """
        self.tenant_spreadsheet = tenant_spreadsheet
        self.tenant = tenant_spreadsheet.tenant
        self._client = None
        self._spreadsheet = None

    def _get_client(self):
        """Google Sheets APIクライアントを取得"""
        if self._client is not None:
            return self._client

        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            raise SpreadsheetSyncError(
                "gspread と google-auth がインストールされていません。"
                "pip install gspread google-auth を実行してください。"
            )

        # サービスアカウント認証情報
        credentials_path = getattr(settings, 'GOOGLE_CREDENTIALS_PATH', None)
        credentials_dict = getattr(settings, 'GOOGLE_CREDENTIALS', None)

        if not credentials_path and not credentials_dict:
            raise SpreadsheetSyncError(
                "Google認証情報が設定されていません。"
                "settings.GOOGLE_CREDENTIALS_PATH または "
                "settings.GOOGLE_CREDENTIALS を設定してください。"
            )

        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            if credentials_dict:
                credentials = Credentials.from_service_account_info(
                    credentials_dict, scopes=scopes
                )
            else:
                credentials = Credentials.from_service_account_file(
                    credentials_path, scopes=scopes
                )

            self._client = gspread.authorize(credentials)
            return self._client

        except Exception as e:
            raise SpreadsheetSyncError(f"Google認証に失敗しました: {e}")

    def _get_spreadsheet(self):
        """スプレッドシートを取得"""
        if self._spreadsheet is not None:
            return self._spreadsheet

        client = self._get_client()
        try:
            self._spreadsheet = client.open_by_key(
                self.tenant_spreadsheet.spreadsheet_id
            )
            return self._spreadsheet
        except Exception as e:
            raise SpreadsheetSyncError(
                f"スプレッドシートを開けませんでした: {e}"
            )

    def _get_or_create_worksheet(self, title: str, columns: list):
        """ワークシートを取得または作成"""
        spreadsheet = self._get_spreadsheet()

        try:
            worksheet = spreadsheet.worksheet(title)
        except Exception:
            # シートが存在しない場合は作成
            worksheet = spreadsheet.add_worksheet(
                title=title,
                rows=1000,
                cols=len(columns)
            )
            # ヘッダー行を設定
            worksheet.update('A1', [columns])
            # ヘッダー行をフリーズ
            worksheet.freeze(rows=1)

        return worksheet

    def sync_all(self) -> dict:
        """全データを同期

        Returns:
            dict: 同期結果サマリー
        """
        if not self.tenant_spreadsheet.is_active:
            raise SpreadsheetSyncError("スプレッドシート接続が無効です。")

        results = {
            'success': True,
            'synced_at': timezone.now(),
            'details': {}
        }

        try:
            results['details']['candidates'] = self.sync_candidates()
            results['details']['applications'] = self.sync_applications()
            results['details']['interviews'] = self.sync_interviews()
            results['details']['jobs'] = self.sync_jobs()
            results['details']['summary'] = self.sync_summary()

            # 同期成功を記録
            self.tenant_spreadsheet.update_sync_time()

        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            self.tenant_spreadsheet.record_sync_error(str(e))
            logger.error(f"スプレッドシート同期エラー: {e}", exc_info=True)

        return results

    def sync_candidates(self) -> dict:
        """候補者データを同期"""
        from apps.candidates.models import Candidate

        worksheet = self._get_or_create_worksheet(
            self.SHEET_CANDIDATES,
            self.CANDIDATE_COLUMNS
        )

        candidates = Candidate.objects.filter(
            tenant=self.tenant,
            is_archived=False
        ).order_by('-created_at')

        rows = []
        for c in candidates:
            rows.append([
                str(c.id)[:8],  # UUID短縮
                c.name or '',
                c.name_kana or '',
                c.email or '',
                c.phone or '',
                c.current_company or '',
                c.current_position or '',
                c.age or '',
                c.get_gender_display() if c.gender else '',
                c.get_employment_status_display() if c.employment_status else '',
                c.created_at.strftime('%Y-%m-%d') if c.created_at else '',
                c.updated_at.strftime('%Y-%m-%d') if c.updated_at else '',
            ])

        # データを更新（ヘッダー行の次から）
        if rows:
            worksheet.update(f'A2:L{len(rows) + 1}', rows)

        return {'count': len(rows)}

    def sync_applications(self) -> dict:
        """応募データを同期"""
        from apps.applications.models import Application

        worksheet = self._get_or_create_worksheet(
            self.SHEET_APPLICATIONS,
            self.APPLICATION_COLUMNS
        )

        applications = Application.objects.filter(
            tenant=self.tenant
        ).select_related(
            'candidate', 'job', 'source', 'agent_company'
        ).order_by('-created_at')

        rows = []
        for a in applications:
            rows.append([
                str(a.id)[:8],
                a.candidate.name if a.candidate else '',
                a.job.title if a.job else '',
                a.get_status_display() if a.status else '',
                a.applied_at.strftime('%Y-%m-%d') if a.applied_at else '',
                a.source.name if a.source else '',
                a.agent_company.name if a.agent_company else '',
                a.updated_at.strftime('%Y-%m-%d') if a.updated_at else '',
            ])

        if rows:
            worksheet.update(f'A2:H{len(rows) + 1}', rows)

        return {'count': len(rows)}

    def sync_interviews(self) -> dict:
        """面接データを同期"""
        from apps.interviews.models import Interview

        worksheet = self._get_or_create_worksheet(
            self.SHEET_INTERVIEWS,
            self.INTERVIEW_COLUMNS
        )

        interviews = Interview.objects.filter(
            tenant=self.tenant
        ).select_related(
            'application__candidate',
            'application__job',
            'interviewer'
        ).order_by('-scheduled_at')

        rows = []
        for i in interviews:
            rows.append([
                str(i.id)[:8],
                i.application.candidate.name if i.application and i.application.candidate else '',
                i.application.job.title if i.application and i.application.job else '',
                i.get_interview_type_display() if i.interview_type else '',
                i.scheduled_at.strftime('%Y-%m-%d %H:%M') if i.scheduled_at else '',
                i.interviewer.get_full_name() if i.interviewer else '',
                i.get_status_display() if i.status else '',
                i.get_result_display() if i.result else '',
                i.updated_at.strftime('%Y-%m-%d') if i.updated_at else '',
            ])

        if rows:
            worksheet.update(f'A2:I{len(rows) + 1}', rows)

        return {'count': len(rows)}

    def sync_jobs(self) -> dict:
        """求人データを同期"""
        from apps.jobs.models import Job

        worksheet = self._get_or_create_worksheet(
            self.SHEET_JOBS,
            self.JOB_COLUMNS
        )

        jobs = Job.objects.filter(
            tenant=self.tenant
        ).order_by('-created_at')

        rows = []
        for j in jobs:
            rows.append([
                str(j.id)[:8],
                j.title or '',
                j.department or '',
                j.get_employment_type_display() if j.employment_type else '',
                j.get_status_display() if j.status else '',
                j.positions or '',
                j.applications.count(),
                j.published_at.strftime('%Y-%m-%d') if j.published_at else '',
                j.deadline.strftime('%Y-%m-%d') if j.deadline else '',
            ])

        if rows:
            worksheet.update(f'A2:I{len(rows) + 1}', rows)

        return {'count': len(rows)}

    def sync_summary(self) -> dict:
        """サマリーシートを同期"""
        from apps.candidates.models import Candidate
        from apps.jobs.models import Job
        from apps.applications.models import Application
        from apps.interviews.models import Interview

        worksheet = self._get_or_create_worksheet(
            self.SHEET_SUMMARY,
            ['項目', '値', '更新日時']
        )

        now = timezone.now().strftime('%Y-%m-%d %H:%M')

        summary_data = [
            ['候補者数', Candidate.objects.filter(tenant=self.tenant).count(), now],
            ['求人数', Job.objects.filter(tenant=self.tenant).count(), now],
            ['公開中求人', Job.objects.filter(tenant=self.tenant, status='published').count(), now],
            ['応募数', Application.objects.filter(tenant=self.tenant).count(), now],
            ['面接数', Interview.objects.filter(tenant=self.tenant).count(), now],
            ['---', '---', '---'],
            ['最終同期', now, ''],
        ]

        worksheet.update('A2:C8', summary_data)

        return {'updated': True}


def sync_tenant_spreadsheet(tenant_spreadsheet_id: str) -> dict:
    """テナントスプレッドシートを同期（Celeryタスク用）

    Args:
        tenant_spreadsheet_id: TenantSpreadsheetのID

    Returns:
        dict: 同期結果
    """
    from apps.tenants.models import TenantSpreadsheet

    try:
        spreadsheet = TenantSpreadsheet.objects.get(id=tenant_spreadsheet_id)
    except TenantSpreadsheet.DoesNotExist:
        return {'success': False, 'error': 'スプレッドシート設定が見つかりません'}

    service = SpreadsheetSyncService(spreadsheet)
    return service.sync_all()
