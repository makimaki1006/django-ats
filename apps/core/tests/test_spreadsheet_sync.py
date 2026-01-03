"""
スプレッドシート同期サービスのテスト

逆証明によるロジック検証:
1. カラムマッピングがモデルフィールドと一致
2. Push時のデータ形式が正しい
3. JSONフィールドのシリアライズが正しい
4. 日付フォーマットが正しい
"""

import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.candidates.models import Candidate, GenderChoices, EmploymentStatusChoices
from apps.jobs.models import Job, JobStatusChoices, EmploymentTypeChoices
from apps.applications.models import Application, ApplicationStatusChoices
from apps.interviews.models import Interview, InterviewTypeChoices, InterviewStatusChoices
from apps.settings_app.models import ApplicationSource
from apps.core.services.spreadsheet_sync import SpreadsheetSyncService


User = get_user_model()


class MockSpreadsheetConnection:
    """テスト用のモック接続"""

    def __init__(self, tenant):
        self.tenant = tenant
        self.spreadsheet_id = 'test-spreadsheet-id'
        self.credentials_json = json.dumps({
            'type': 'service_account',
            'project_id': 'test-project',
            'private_key_id': 'test-key-id',
            'private_key': '-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n',
            'client_email': 'test@test.iam.gserviceaccount.com',
            'client_id': '123456789',
        })
        self.sync_candidates = True
        self.sync_jobs = True
        self.sync_applications = True
        self.sync_interviews = True
        self.auto_sync_enabled = True
        self.spreadsheet_name = 'テストシート'

    def mark_syncing(self):
        pass

    def mark_synced(self):
        pass

    def mark_error(self, error):
        pass

    def save(self, **kwargs):
        pass


class CandidateColumnMappingTest(TestCase):
    """候補者カラムマッピングのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_candidate_columns_match_model_fields(self):
        """CANDIDATE_COLUMNSがCandidateモデルのフィールドと一致"""
        expected_columns = {
            'id', 'name', 'name_kana', 'email', 'phone', 'birth_date',
            'gender', 'address', 'current_company', 'current_position',
            'employment_status', 'years_of_experience', 'desired_salary',
            'desired_positions', 'desired_locations', 'skills',
            'qualifications', 'education', 'notes',
        }

        actual_columns = set(SpreadsheetSyncService.CANDIDATE_COLUMNS.keys())

        self.assertEqual(expected_columns, actual_columns)

    def test_candidate_model_has_all_mapped_fields(self):
        """Candidateモデルにマッピングされたすべてのフィールドが存在"""
        candidate = Candidate(tenant=self.tenant, name='テスト', email='test@example.com')

        for field_name in SpreadsheetSyncService.CANDIDATE_COLUMNS.values():
            self.assertTrue(
                hasattr(candidate, field_name),
                f"Candidateモデルにフィールド '{field_name}' が存在しません"
            )


class JobColumnMappingTest(TestCase):
    """求人カラムマッピングのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_job_columns_match_model_fields(self):
        """JOB_COLUMNSがJobモデルのフィールドと一致"""
        expected_columns = {
            'id', 'unique_code', 'title', 'department', 'team',
            'employment_type', 'location', 'remote_policy',
            'salary_min', 'salary_max', 'description', 'requirements',
            'preferred_requirements', 'benefits', 'headcount', 'status',
        }

        actual_columns = set(SpreadsheetSyncService.JOB_COLUMNS.keys())

        self.assertEqual(expected_columns, actual_columns)

    def test_job_model_has_all_mapped_fields(self):
        """Jobモデルにマッピングされたすべてのフィールドが存在"""
        job = Job(tenant=self.tenant, title='テスト求人', unique_code='TEST-001')

        for field_name in SpreadsheetSyncService.JOB_COLUMNS.values():
            self.assertTrue(
                hasattr(job, field_name),
                f"Jobモデルにフィールド '{field_name}' が存在しません"
            )


class ApplicationColumnMappingTest(TestCase):
    """応募カラムマッピングのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト候補者',
            email='test@example.com',
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
        )

    def test_application_columns_expected(self):
        """APPLICATION_COLUMNSが期待通り"""
        expected_columns = {
            'id', 'candidate_id', 'candidate_name', 'job_id', 'job_title',
            'status', 'source', 'applied_at', 'evaluation_score',
            'evaluation_notes', 'notes',
        }

        actual_columns = set(SpreadsheetSyncService.APPLICATION_COLUMNS.keys())

        self.assertEqual(expected_columns, actual_columns)

    def test_application_display_columns_are_none(self):
        """表示用カラムはNone"""
        self.assertIsNone(SpreadsheetSyncService.APPLICATION_COLUMNS['candidate_name'])
        self.assertIsNone(SpreadsheetSyncService.APPLICATION_COLUMNS['job_title'])


class InterviewColumnMappingTest(TestCase):
    """面接カラムマッピングのテスト"""

    def test_interview_columns_expected(self):
        """INTERVIEW_COLUMNSが期待通り"""
        expected_columns = {
            'id', 'application_id', 'candidate_name', 'job_title',
            'interview_type', 'interview_round', 'scheduled_at',
            'duration_minutes', 'location', 'status', 'result',
            'feedback', 'evaluation_score', 'internal_notes',
        }

        actual_columns = set(SpreadsheetSyncService.INTERVIEW_COLUMNS.keys())

        self.assertEqual(expected_columns, actual_columns)

    def test_interview_display_columns_are_none(self):
        """表示用カラムはNone"""
        self.assertIsNone(SpreadsheetSyncService.INTERVIEW_COLUMNS['candidate_name'])
        self.assertIsNone(SpreadsheetSyncService.INTERVIEW_COLUMNS['job_title'])


class PushCandidatesTest(TestCase):
    """候補者エクスポートのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_push_candidates_row_format(self):
        """候補者の行データ形式が正しい"""
        # 候補者作成
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='山田太郎',
            name_kana='ヤマダタロウ',
            email='yamada@example.com',
            phone='+819012345678',
            birth_date=date(1990, 1, 15),
            gender=GenderChoices.MALE,
            address='東京都渋谷区',
            current_company='株式会社テスト',
            current_position='エンジニア',
            employment_status=EmploymentStatusChoices.EMPLOYED,
            years_of_experience=5,
            desired_salary=600,
            desired_positions=['バックエンドエンジニア', 'フルスタックエンジニア'],
            desired_locations=['東京', '大阪'],
            skills=['Python', 'Django', 'AWS'],
            qualifications=['基本情報技術者'],
            education='大学卒',
            notes='優秀な候補者',
        )

        # モックワークシート
        mock_worksheet = MagicMock()
        captured_data = []

        def capture_update(data, cell):
            captured_data.extend(data)

        mock_worksheet.update = capture_update
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_candidates()

        # 検証
        self.assertEqual(count, 1)
        self.assertEqual(len(captured_data), 2)  # ヘッダー + 1行

        # ヘッダー検証
        headers = captured_data[0]
        self.assertIn('id', headers)
        self.assertIn('name', headers)
        self.assertIn('email', headers)
        self.assertIn('employment_status', headers)
        self.assertIn('desired_positions', headers)

        # データ行検証
        row = captured_data[1]
        self.assertEqual(row[1], '山田太郎')  # name
        self.assertEqual(row[3], 'yamada@example.com')  # email
        self.assertEqual(row[10], 'employed')  # employment_status

    def test_push_candidates_json_fields_serialized(self):
        """JSONフィールドが正しくシリアライズされる"""
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            skills=['Python', 'JavaScript'],
            desired_positions=['エンジニア'],
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        # skillsカラムの位置を確認（インデックス15）
        skills_json = row[15]

        # JSONとしてパース可能であることを確認
        parsed = json.loads(skills_json)
        self.assertEqual(parsed, ['Python', 'JavaScript'])

    def test_push_candidates_empty_json_fields(self):
        """空のJSONフィールドが空文字になる"""
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test2@example.com',
            skills=[],
            desired_positions=[],
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        # 空のJSONフィールドは空文字
        self.assertEqual(row[15], '')  # skills
        self.assertEqual(row[13], '')  # desired_positions


class PushJobsTest(TestCase):
    """求人エクスポートのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_push_jobs_row_format(self):
        """求人の行データ形式が正しい"""
        job = Job.objects.create(
            tenant=self.tenant,
            title='バックエンドエンジニア',
            unique_code='BE-001',
            department='開発部',
            team='プラットフォームチーム',
            employment_type=EmploymentTypeChoices.FULL_TIME,
            location='東京都渋谷区',
            remote_policy='フルリモート可',
            salary_min=500,
            salary_max=800,
            description='バックエンド開発をお任せします',
            requirements='Python3年以上',
            preferred_requirements='AWS経験あれば尚可',
            benefits='社保完備、リモート可',
            headcount=3,
            status=JobStatusChoices.ACTIVE,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_jobs()

        self.assertEqual(count, 1)

        # ヘッダー検証
        headers = captured_data[0]
        self.assertIn('unique_code', headers)
        self.assertIn('remote_policy', headers)

        # データ行検証
        row = captured_data[1]
        self.assertEqual(row[1], 'BE-001')  # unique_code
        self.assertEqual(row[2], 'バックエンドエンジニア')  # title
        self.assertEqual(row[7], 'フルリモート可')  # remote_policy
        self.assertEqual(row[8], '500')  # salary_min
        self.assertEqual(row[9], '800')  # salary_max


class PushApplicationsTest(TestCase):
    """応募エクスポートのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='山田太郎',
            email='yamada@example.com',
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='エンジニア',
            unique_code='ENG-001',
        )
        self.source = ApplicationSource.objects.create(
            tenant=self.tenant,
            name='エージェント経由',
            source_type='agent',
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_push_applications_with_source(self):
        """応募のソース（ForeignKey）が正しく名前に変換される"""
        application = Application.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            job=self.job,
            source=self.source,
            status=ApplicationStatusChoices.DOCUMENT_SCREENING,
            evaluation_score=4,
            evaluation_notes='良い候補者',
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_applications()

        self.assertEqual(count, 1)

        row = captured_data[1]
        self.assertEqual(row[2], '山田太郎')  # candidate_name
        self.assertEqual(row[4], 'エンジニア')  # job_title
        self.assertEqual(row[6], 'エージェント経由')  # source name

    def test_push_applications_without_source(self):
        """ソースがない場合は空文字"""
        application = Application.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            job=self.job,
            source=None,
            status=ApplicationStatusChoices.NEW,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_applications()

        row = captured_data[1]
        self.assertEqual(row[6], '')  # source is empty


class PushInterviewsTest(TestCase):
    """面接エクスポートのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='山田太郎',
            email='yamada@example.com',
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='エンジニア',
            unique_code='ENG-001',
        )
        self.application = Application.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            job=self.job,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_push_interviews_row_format(self):
        """面接の行データ形式が正しい"""
        interview = Interview.objects.create(
            tenant=self.tenant,
            application=self.application,
            interview_type=InterviewTypeChoices.VIDEO,
            interview_round=1,
            scheduled_at=timezone.now(),
            duration_minutes=60,
            location='Zoom',
            status=InterviewStatusChoices.SCHEDULED,
            feedback='良い印象',
            evaluation_score=4,
            internal_notes='次回に進める',
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_interviews()

        self.assertEqual(count, 1)

        # ヘッダー検証
        headers = captured_data[0]
        self.assertIn('interview_round', headers)
        self.assertIn('evaluation_score', headers)
        self.assertIn('internal_notes', headers)
        self.assertNotIn('round_number', headers)  # 古いカラム名でないこと
        self.assertNotIn('score', headers)  # 古いカラム名でないこと
        self.assertNotIn('notes', headers)  # 古いカラム名でないこと

        # データ行検証
        row = captured_data[1]
        self.assertEqual(row[2], '山田太郎')  # candidate_name
        self.assertEqual(row[3], 'エンジニア')  # job_title
        self.assertEqual(row[5], '1')  # interview_round
        self.assertEqual(row[12], '4')  # evaluation_score
        self.assertEqual(row[13], '次回に進める')  # internal_notes


class DateParsingTest(TestCase):
    """日付パースのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_parse_iso_date(self):
        """ISO 8601形式の日付をパース"""
        result = self.service._parse_date('2024-01-15T10:30:00')
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_simple_date(self):
        """YYYY-MM-DD形式の日付をパース"""
        result = self.service._parse_date('2024-01-15')
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_parse_empty_date(self):
        """空文字列はNone"""
        result = self.service._parse_date('')
        self.assertIsNone(result)

    def test_parse_invalid_date(self):
        """無効な日付はNone"""
        result = self.service._parse_date('invalid-date')
        self.assertIsNone(result)


class IntParsingTest(TestCase):
    """整数パースのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_parse_int(self):
        """整数文字列をパース"""
        result = self.service._parse_int('123')
        self.assertEqual(result, 123)

    def test_parse_float_to_int(self):
        """浮動小数点を整数に変換"""
        result = self.service._parse_int('123.45')
        self.assertEqual(result, 123)

    def test_parse_empty_int(self):
        """空文字列はNone"""
        result = self.service._parse_int('')
        self.assertIsNone(result)

    def test_parse_invalid_int(self):
        """無効な文字列はNone"""
        result = self.service._parse_int('abc')
        self.assertIsNone(result)


class PushToSpreadsheetIntegrationTest(TestCase):
    """push_to_spreadsheet統合テスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_push_all_models(self):
        """全モデルのPush"""
        # テストデータ作成
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト候補者',
            email='test@example.com',
        )
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
        )

        mock_worksheet = MagicMock()
        mock_worksheet.update = MagicMock()
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            results = self.service.push_to_spreadsheet()

        self.assertIn('candidates', results)
        self.assertIn('jobs', results)
        self.assertEqual(results['candidates'], 1)
        self.assertEqual(results['jobs'], 1)

    def test_push_specific_model(self):
        """特定モデルのみPush"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト候補者',
            email='test@example.com',
        )

        mock_worksheet = MagicMock()
        mock_worksheet.update = MagicMock()
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            results = self.service.push_to_spreadsheet('candidates')

        self.assertIn('candidates', results)
        self.assertNotIn('jobs', results)


class SheetMappingTest(TestCase):
    """シートマッピングのテスト"""

    def test_sheet_mapping(self):
        """SHEET_MAPPINGが正しい"""
        expected = {
            '候補者': 'candidates',
            '求人': 'jobs',
            '応募': 'applications',
            '面接': 'interviews',
            '設定': 'settings',
        }

        self.assertEqual(SpreadsheetSyncService.SHEET_MAPPING, expected)


# =============================================================================
# 追加テスト: エッジケース
# =============================================================================

class EmptyDataTest(TestCase):
    """空データのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_push_candidates_no_data(self):
        """候補者がいない場合は0件"""
        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_candidates()

        self.assertEqual(count, 0)
        self.assertEqual(len(captured_data), 1)  # ヘッダーのみ

    def test_push_jobs_no_data(self):
        """求人がない場合は0件"""
        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_jobs()

        self.assertEqual(count, 0)

    def test_push_applications_no_data(self):
        """応募がない場合は0件"""
        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_applications()

        self.assertEqual(count, 0)

    def test_push_interviews_no_data(self):
        """面接がない場合は0件"""
        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_interviews()

        self.assertEqual(count, 0)


class MultipleRecordsTest(TestCase):
    """複数レコードのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_push_multiple_candidates(self):
        """複数候補者のエクスポート"""
        for i in range(5):
            Candidate.objects.create(
                tenant=self.tenant,
                name=f'候補者{i}',
                email=f'candidate{i}@example.com',
            )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_candidates()

        self.assertEqual(count, 5)
        self.assertEqual(len(captured_data), 6)  # ヘッダー + 5行

    def test_push_multiple_jobs(self):
        """複数求人のエクスポート"""
        for i in range(3):
            Job.objects.create(
                tenant=self.tenant,
                title=f'求人{i}',
                unique_code=f'JOB-{i:03d}',
            )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_jobs()

        self.assertEqual(count, 3)


class NullValueTest(TestCase):
    """Null値のテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_candidate_null_birth_date(self):
        """生年月日がNullの場合"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            birth_date=None,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_candidates()

        self.assertEqual(count, 1)
        row = captured_data[1]
        self.assertEqual(row[5], '')  # birth_date is empty string

    def test_candidate_null_optional_fields(self):
        """オプションフィールドがNullの場合"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            address='',
            current_company='',
            years_of_experience=None,
            desired_salary=None,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_candidates()

        self.assertEqual(count, 1)

    def test_job_null_salary(self):
        """給与がNullの場合"""
        Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
            salary_min=None,
            salary_max=None,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_jobs()

        self.assertEqual(count, 1)
        row = captured_data[1]
        self.assertEqual(row[8], '')  # salary_min is empty
        self.assertEqual(row[9], '')  # salary_max is empty


class SpecialCharacterTest(TestCase):
    """特殊文字のテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_candidate_with_japanese_name(self):
        """日本語名の候補者"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='田中太郎',
            name_kana='タナカタロウ',
            email='tanaka@example.com',
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_candidates()

        self.assertEqual(count, 1)
        row = captured_data[1]
        self.assertEqual(row[1], '田中太郎')
        self.assertEqual(row[2], 'タナカタロウ')

    def test_candidate_with_special_chars_in_notes(self):
        """備考に特殊文字を含む"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            notes='備考: "テスト" & <特殊文字>',
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_candidates()

        self.assertEqual(count, 1)
        row = captured_data[1]
        self.assertIn('備考', row[18])

    def test_job_with_emoji(self):
        """求人タイトルに絵文字を含む"""
        Job.objects.create(
            tenant=self.tenant,
            title='🎯 エンジニア募集',
            unique_code='EMOJI-001',
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_jobs()

        self.assertEqual(count, 1)
        row = captured_data[1]
        self.assertIn('🎯', row[2])


class TenantIsolationTest(TestCase):
    """テナント分離のテスト"""

    def setUp(self):
        self.tenant1 = Tenant.objects.create(
            name='テナント1',
            code='tenant-1',
            is_active=True,
        )
        self.tenant2 = Tenant.objects.create(
            name='テナント2',
            code='tenant-2',
            is_active=True,
        )

    def test_candidates_filtered_by_tenant(self):
        """候補者がテナントでフィルタリングされる"""
        # テナント1の候補者
        Candidate.objects.create(
            tenant=self.tenant1,
            name='テナント1候補者',
            email='t1@example.com',
        )
        # テナント2の候補者
        Candidate.objects.create(
            tenant=self.tenant2,
            name='テナント2候補者',
            email='t2@example.com',
        )

        connection = MockSpreadsheetConnection(self.tenant1)
        service = SpreadsheetSyncService(connection)

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(service, '_get_worksheet', return_value=mock_worksheet):
            count = service.push_candidates()

        self.assertEqual(count, 1)
        row = captured_data[1]
        self.assertEqual(row[1], 'テナント1候補者')

    def test_jobs_filtered_by_tenant(self):
        """求人がテナントでフィルタリングされる"""
        Job.objects.create(
            tenant=self.tenant1,
            title='テナント1求人',
            unique_code='T1-001',
        )
        Job.objects.create(
            tenant=self.tenant2,
            title='テナント2求人',
            unique_code='T2-001',
        )

        connection = MockSpreadsheetConnection(self.tenant1)
        service = SpreadsheetSyncService(connection)

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(service, '_get_worksheet', return_value=mock_worksheet):
            count = service.push_jobs()

        self.assertEqual(count, 1)
        row = captured_data[1]
        self.assertEqual(row[2], 'テナント1求人')


class ColumnOrderTest(TestCase):
    """カラム順序のテスト"""

    def test_candidate_column_order(self):
        """候補者カラムの順序"""
        columns = list(SpreadsheetSyncService.CANDIDATE_COLUMNS.keys())
        self.assertEqual(columns[0], 'id')
        self.assertEqual(columns[1], 'name')
        self.assertEqual(columns[2], 'name_kana')
        self.assertEqual(columns[3], 'email')

    def test_job_column_order(self):
        """求人カラムの順序"""
        columns = list(SpreadsheetSyncService.JOB_COLUMNS.keys())
        self.assertEqual(columns[0], 'id')
        self.assertEqual(columns[1], 'unique_code')
        self.assertEqual(columns[2], 'title')

    def test_application_column_order(self):
        """応募カラムの順序"""
        columns = list(SpreadsheetSyncService.APPLICATION_COLUMNS.keys())
        self.assertEqual(columns[0], 'id')
        self.assertEqual(columns[1], 'candidate_id')
        self.assertEqual(columns[2], 'candidate_name')

    def test_interview_column_order(self):
        """面接カラムの順序"""
        columns = list(SpreadsheetSyncService.INTERVIEW_COLUMNS.keys())
        self.assertEqual(columns[0], 'id')
        self.assertEqual(columns[1], 'application_id')
        self.assertEqual(columns[2], 'candidate_name')


class JSONFieldSerializationTest(TestCase):
    """JSONフィールドシリアライズのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_skills_json_format(self):
        """skillsがJSON形式でシリアライズされる"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            skills=['Python', 'Django', 'React'],
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        skills_json = row[15]
        parsed = json.loads(skills_json)
        self.assertIn('Python', parsed)
        self.assertIn('Django', parsed)
        self.assertIn('React', parsed)

    def test_desired_locations_json_format(self):
        """desired_locationsがJSON形式でシリアライズされる"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            desired_locations=['東京', '大阪', '福岡'],
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        locations_json = row[14]
        parsed = json.loads(locations_json)
        self.assertEqual(len(parsed), 3)

    def test_qualifications_json_format(self):
        """qualificationsがJSON形式でシリアライズされる"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            qualifications=['基本情報技術者', '応用情報技術者'],
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        quals_json = row[16]
        parsed = json.loads(quals_json)
        self.assertEqual(len(parsed), 2)


class DateFormattingTest(TestCase):
    """日付フォーマットのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_birth_date_format(self):
        """生年月日のフォーマット"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            birth_date=date(1990, 5, 15),
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        self.assertEqual(row[5], '1990-05-15')

    def test_scheduled_at_datetime_format(self):
        """面接日時のフォーマット"""
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
        )
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
        )
        application = Application.objects.create(
            tenant=self.tenant,
            candidate=candidate,
            job=job,
        )
        Interview.objects.create(
            tenant=self.tenant,
            application=application,
            interview_type=InterviewTypeChoices.VIDEO,
            interview_round=1,
            scheduled_at=timezone.make_aware(datetime(2024, 6, 15, 14, 30, 0)),
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_interviews()

        row = captured_data[1]
        # 日時が含まれていることを確認
        self.assertIn('2024', row[6])


class IntegerFormattingTest(TestCase):
    """整数フォーマットのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_years_of_experience_format(self):
        """経験年数のフォーマット"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            years_of_experience=10,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        self.assertEqual(row[11], '10')

    def test_zero_years_of_experience(self):
        """経験年数0の場合（0は空文字に変換される）"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            years_of_experience=0,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        # 現在の実装では0はfalsyなので空文字に変換される
        self.assertEqual(row[11], '')

    def test_headcount_format(self):
        """採用人数のフォーマット"""
        Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
            headcount=5,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_jobs()

        row = captured_data[1]
        self.assertEqual(row[14], '5')


class EnumValueTest(TestCase):
    """Enum値のテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_gender_enum_value(self):
        """性別Enumが文字列で出力される"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            gender=GenderChoices.FEMALE,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        self.assertEqual(row[6], 'female')

    def test_employment_status_enum_value(self):
        """就業状況Enumが文字列で出力される"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            employment_status=EmploymentStatusChoices.UNEMPLOYED,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_candidates()

        row = captured_data[1]
        self.assertEqual(row[10], 'unemployed')

    def test_job_status_enum_value(self):
        """求人ステータスEnumが文字列で出力される"""
        Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
            status=JobStatusChoices.CLOSED,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_jobs()

        row = captured_data[1]
        self.assertEqual(row[15], 'closed')

    def test_interview_type_enum_value(self):
        """面接タイプEnumが文字列で出力される"""
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
        )
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
        )
        application = Application.objects.create(
            tenant=self.tenant,
            candidate=candidate,
            job=job,
        )
        Interview.objects.create(
            tenant=self.tenant,
            application=application,
            interview_type=InterviewTypeChoices.IN_PERSON,
            interview_round=1,
            scheduled_at=timezone.now(),
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_interviews()

        row = captured_data[1]
        self.assertEqual(row[4], 'in_person')


class SyncFlagTest(TestCase):
    """同期フラグのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_sync_candidates_disabled(self):
        """候補者同期が無効の場合スキップ"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
        )

        connection = MockSpreadsheetConnection(self.tenant)
        connection.sync_candidates = False
        service = SpreadsheetSyncService(connection)

        mock_worksheet = MagicMock()
        mock_worksheet.update = MagicMock()
        mock_worksheet.clear = MagicMock()

        with patch.object(service, '_get_worksheet', return_value=mock_worksheet):
            results = service.push_to_spreadsheet()

        self.assertNotIn('candidates', results)

    def test_sync_jobs_disabled(self):
        """求人同期が無効の場合スキップ"""
        Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
        )

        connection = MockSpreadsheetConnection(self.tenant)
        connection.sync_jobs = False
        service = SpreadsheetSyncService(connection)

        mock_worksheet = MagicMock()
        mock_worksheet.update = MagicMock()
        mock_worksheet.clear = MagicMock()

        with patch.object(service, '_get_worksheet', return_value=mock_worksheet):
            results = service.push_to_spreadsheet()

        self.assertNotIn('jobs', results)


class ApplicationRelationTest(TestCase):
    """応募の関連データテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_application_candidate_name_displayed(self):
        """応募に候補者名が表示される"""
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='山田花子',
            email='hanako@example.com',
        )
        job = Job.objects.create(
            tenant=self.tenant,
            title='デザイナー',
            unique_code='DES-001',
        )
        Application.objects.create(
            tenant=self.tenant,
            candidate=candidate,
            job=job,
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_applications()

        row = captured_data[1]
        self.assertEqual(row[2], '山田花子')
        self.assertEqual(row[4], 'デザイナー')

    def test_application_status_values(self):
        """応募ステータスの各値"""
        statuses = [
            ApplicationStatusChoices.NEW,
            ApplicationStatusChoices.DOCUMENT_SCREENING,
            ApplicationStatusChoices.DOCUMENT_PASSED,
        ]

        for i, status in enumerate(statuses):
            candidate = Candidate.objects.create(
                tenant=self.tenant,
                name=f'テスト{i}',
                email=f'test{i}@example.com',
            )
            job = Job.objects.create(
                tenant=self.tenant,
                title=f'テスト求人{i}',
                unique_code=f'TEST-{i:03d}',
            )
            Application.objects.create(
                tenant=self.tenant,
                candidate=candidate,
                job=job,
                status=status,
            )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_applications()

        self.assertEqual(count, 3)


class InterviewRelationTest(TestCase):
    """面接の関連データテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='佐藤次郎',
            email='jiro@example.com',
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='マネージャー',
            unique_code='MGR-001',
        )
        self.application = Application.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            job=self.job,
        )
        self.connection = MockSpreadsheetConnection(self.tenant)
        self.service = SpreadsheetSyncService(self.connection)

    def test_interview_candidate_and_job_displayed(self):
        """面接に候補者名と求人タイトルが表示される"""
        Interview.objects.create(
            tenant=self.tenant,
            application=self.application,
            interview_type=InterviewTypeChoices.VIDEO,
            interview_round=1,
            scheduled_at=timezone.now(),
        )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            self.service.push_interviews()

        row = captured_data[1]
        self.assertEqual(row[2], '佐藤次郎')
        self.assertEqual(row[3], 'マネージャー')

    def test_multiple_interview_rounds(self):
        """複数回の面接"""
        for i in range(1, 4):
            Interview.objects.create(
                tenant=self.tenant,
                application=self.application,
                interview_type=InterviewTypeChoices.VIDEO,
                interview_round=i,
                scheduled_at=timezone.now(),
            )

        mock_worksheet = MagicMock()
        captured_data = []
        mock_worksheet.update = lambda data, cell: captured_data.extend(data)
        mock_worksheet.clear = MagicMock()

        with patch.object(self.service, '_get_worksheet', return_value=mock_worksheet):
            count = self.service.push_interviews()

        self.assertEqual(count, 3)
        # 回数が正しいか確認
        rounds = [captured_data[i][5] for i in range(1, 4)]
        self.assertIn('1', rounds)
        self.assertIn('2', rounds)
        self.assertIn('3', rounds)
