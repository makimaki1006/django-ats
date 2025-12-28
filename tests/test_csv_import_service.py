"""Django ATS - CSVインポートサービス ユニットテスト

CandidateCSVImporter のテストケース。
カバレッジ目標: 25% → 80%

テスト対象:
- 基本インポート機能（日本語/英語ヘッダー）
- 必須フィールド検証
- フィールド変換（性別、就業状況、数値等）
- 重複スキップ処理
- エンコーディング（UTF-8、Shift-JIS）
- ドライラン機能
- バリデーション専用モード
- テンプレートCSV生成
- エラーハンドリング
"""

import pytest
import io
from unittest.mock import MagicMock, patch

from apps.candidates.services import (
    CandidateCSVImporter,
    CSVImportError,
    CSVFieldMapping,
)
from apps.candidates.models import (
    Candidate,
    ImportHistory,
    GenderChoices,
    EmploymentStatusChoices,
)
from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='テストテナント',
        code='test-csv',
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """テストユーザー"""
    return CustomUser.objects.create_user(
        email='csv-test@example.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def importer(tenant, user):
    """CSVインポーターインスタンス"""
    return CandidateCSVImporter(tenant=tenant, user=user)


@pytest.fixture
def valid_japanese_csv():
    """有効な日本語CSVデータ"""
    csv_content = """氏名,氏名（カナ）,メールアドレス,電話番号,性別,生年月日,住所,現職企業,現職役職,就業状況,経験年数,希望年収,スキル,資格,最終学歴,履歴書URL,職務経歴書URL,備考
山田太郎,ヤマダタロウ,yamada@example.com,09012345678,男性,1990-01-01,東京都渋谷区,株式会社ABC,エンジニア,就業中,10,600,Python,基本情報技術者,東京大学,https://example.com/resume,https://example.com/cv,転職希望
佐藤花子,サトウハナコ,sato@example.com,09087654321,女性,1992-05-15,大阪府大阪市,株式会社DEF,デザイナー,離職中,5,500,Figma,色彩検定,京都大学,,,キャリアアップ希望"""
    return io.StringIO(csv_content)


@pytest.fixture
def valid_english_csv():
    """有効な英語CSVデータ"""
    csv_content = """name,name_kana,email,phone,gender,birth_date,address,current_company,current_position,employment_status,years_of_experience,desired_salary,skills,qualifications,education,resume_url,cv_url,notes
John Doe,ジョンドゥ,john@example.com,09012345678,male,1985-03-20,Tokyo,ABC Corp,Manager,employed,15,800,JavaScript,PMP,MIT,,,Looking for new opportunity"""
    return io.StringIO(csv_content)


@pytest.fixture
def csv_missing_required():
    """必須フィールドが欠けているCSV"""
    csv_content = """氏名,氏名（カナ）,メールアドレス,電話番号
,ヤマダタロウ,yamada@example.com,09012345678
山田太郎,ヤマダタロウ,,09012345678"""
    return io.StringIO(csv_content)


@pytest.fixture
def csv_with_duplicates():
    """重複メールアドレスを含むCSV"""
    csv_content = """氏名,メールアドレス
山田太郎,duplicate@example.com
佐藤花子,sato@example.com
鈴木一郎,duplicate@example.com"""
    return io.StringIO(csv_content)


@pytest.fixture
def empty_csv():
    """空のCSV（ヘッダーのみ）"""
    csv_content = """氏名,メールアドレス"""
    return io.StringIO(csv_content)


@pytest.fixture
def csv_with_transform_values():
    """変換が必要な値を含むCSV"""
    csv_content = """氏名,メールアドレス,性別,就業状況,経験年数,希望年収
田中一郎,tanaka@example.com,男性,就業中,10,600
山本二郎,yamamoto@example.com,女性,離職中,abc,invalid
木村三郎,kimura@example.com,その他,フリーランス,5,500"""
    return io.StringIO(csv_content)


# =============================================================================
# 基本インポート機能テスト
# =============================================================================

class TestCandidateCSVImporterBasic:
    """基本インポート機能のテスト"""

    @pytest.mark.django_db
    def test_import_valid_japanese_csv(self, importer, valid_japanese_csv):
        """日本語ヘッダーCSVの正常インポート"""
        history = importer.import_csv(valid_japanese_csv)

        assert history.status == ImportHistory.StatusChoices.COMPLETED
        assert history.total_rows == 2
        assert history.success_count == 2
        assert history.error_count == 0

        # 候補者が作成されていることを確認
        assert Candidate.objects.filter(email='yamada@example.com').exists()
        assert Candidate.objects.filter(email='sato@example.com').exists()

    @pytest.mark.django_db
    def test_import_valid_english_csv(self, importer, valid_english_csv):
        """英語ヘッダーCSVの正常インポート"""
        history = importer.import_csv(valid_english_csv)

        assert history.status == ImportHistory.StatusChoices.COMPLETED
        assert history.total_rows == 1
        assert history.success_count == 1
        assert history.error_count == 0

        candidate = Candidate.objects.get(email='john@example.com')
        assert candidate.name == 'John Doe'

    @pytest.mark.django_db
    def test_import_empty_csv(self, importer, empty_csv):
        """空のCSVのインポート"""
        history = importer.import_csv(empty_csv)

        assert history.status == ImportHistory.StatusChoices.COMPLETED
        assert history.total_rows == 0
        assert history.success_count == 0

    @pytest.mark.django_db
    def test_import_history_created(self, importer, valid_japanese_csv):
        """インポート履歴が作成されること"""
        history = importer.import_csv(valid_japanese_csv)

        assert history.id is not None
        assert history.tenant == importer.tenant
        assert history.created_by == importer.user
        assert history.started_at is not None
        assert history.completed_at is not None

    @pytest.mark.django_db
    def test_import_candidate_tenant_association(self, importer, valid_japanese_csv):
        """候補者がテナントに紐づくこと"""
        importer.import_csv(valid_japanese_csv)

        candidates = Candidate.objects.filter(tenant=importer.tenant)
        assert candidates.count() == 2


# =============================================================================
# 必須フィールド検証テスト
# =============================================================================

class TestRequiredFieldValidation:
    """必須フィールド検証のテスト"""

    @pytest.mark.django_db
    def test_missing_required_name(self, importer, csv_missing_required):
        """必須フィールド（氏名）が空の場合エラー"""
        history = importer.import_csv(csv_missing_required)

        # 両行とも失敗の場合はFAILED、一部成功の場合はPARTIAL
        assert history.status in [ImportHistory.StatusChoices.PARTIAL, ImportHistory.StatusChoices.FAILED]
        assert history.error_count >= 1

        # エラーログに行番号とフィールド名が含まれること
        error_log = history.error_log
        assert any("氏名" in str(e.get('error', '')) or e.get('field') == '氏名' for e in error_log)

    @pytest.mark.django_db
    def test_missing_required_email(self, importer, csv_missing_required):
        """必須フィールド（メールアドレス）が空の場合エラー"""
        history = importer.import_csv(csv_missing_required)

        assert history.error_count >= 1
        # メールアドレスが空の行がエラーになること
        error_log = history.error_log
        assert any("メールアドレス" in str(e.get('error', '')) or e.get('field') == 'メールアドレス' for e in error_log)


# =============================================================================
# フィールド変換テスト
# =============================================================================

class TestFieldTransformations:
    """フィールド変換のテスト"""

    @pytest.mark.django_db
    def test_gender_transformation_male(self, importer, tenant, user):
        """性別変換: 男性 → MALE"""
        csv = io.StringIO("氏名,メールアドレス,性別\n山田太郎,yamada@example.com,男性")
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='yamada@example.com')
        assert candidate.gender == GenderChoices.MALE

    @pytest.mark.django_db
    def test_gender_transformation_female(self, importer):
        """性別変換: 女性 → FEMALE"""
        csv = io.StringIO("氏名,メールアドレス,性別\n佐藤花子,sato@example.com,女性")
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='sato@example.com')
        assert candidate.gender == GenderChoices.FEMALE

    @pytest.mark.django_db
    def test_gender_transformation_other(self, importer):
        """性別変換: その他 → UNSPECIFIED（デフォルト）"""
        csv = io.StringIO("氏名,メールアドレス,性別\n田中一郎,tanaka@example.com,その他")
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='tanaka@example.com')
        # 「その他」はマッピングにないのでUNSPECIFIED
        assert candidate.gender == GenderChoices.UNSPECIFIED

    @pytest.mark.django_db
    def test_employment_status_employed(self, importer):
        """就業状況変換: 就業中 → EMPLOYED"""
        csv = io.StringIO("氏名,メールアドレス,就業状況\n山田太郎,yamada@example.com,就業中")
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='yamada@example.com')
        assert candidate.employment_status == EmploymentStatusChoices.EMPLOYED

    @pytest.mark.django_db
    def test_employment_status_unemployed(self, importer):
        """就業状況変換: 離職中 → UNEMPLOYED"""
        csv = io.StringIO("氏名,メールアドレス,就業状況\n山田太郎,yamada@example.com,離職中")
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='yamada@example.com')
        assert candidate.employment_status == EmploymentStatusChoices.UNEMPLOYED

    @pytest.mark.django_db
    def test_years_of_experience_transformation(self, importer):
        """経験年数の数値変換"""
        csv = io.StringIO("氏名,メールアドレス,経験年数\n山田太郎,yamada@example.com,10")
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='yamada@example.com')
        assert candidate.years_of_experience == 10

    @pytest.mark.django_db
    def test_years_of_experience_invalid(self, importer):
        """経験年数に無効な値（非数値）→ None"""
        csv = io.StringIO("氏名,メールアドレス,経験年数\n山田太郎,yamada@example.com,abc")
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='yamada@example.com')
        assert candidate.years_of_experience is None

    @pytest.mark.django_db
    def test_salary_transformation(self, importer):
        """希望年収の数値変換"""
        csv = io.StringIO("氏名,メールアドレス,希望年収\n山田太郎,yamada@example.com,600")
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='yamada@example.com')
        assert candidate.desired_salary == 600

    @pytest.mark.django_db
    def test_skills_transformation(self, importer):
        """スキルの配列変換（カンマ区切り）"""
        # CSV内でカンマを含む値は引用符で囲む
        csv = io.StringIO('氏名,メールアドレス,スキル\n山田太郎,yamada@example.com,"Python, JavaScript, SQL"')
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='yamada@example.com')
        assert candidate.skills == ['Python', 'JavaScript', 'SQL']

    @pytest.mark.django_db
    def test_qualifications_transformation(self, importer):
        """資格の配列変換（カンマ区切り）"""
        # CSV内でカンマを含む値は引用符で囲む
        csv = io.StringIO('氏名,メールアドレス,資格\n山田太郎,yamada@example.com,"基本情報技術者, 応用情報技術者"')
        importer.import_csv(csv)

        candidate = Candidate.objects.get(email='yamada@example.com')
        assert candidate.qualifications == ['基本情報技術者', '応用情報技術者']


# =============================================================================
# 重複スキップテスト
# =============================================================================

class TestDuplicateHandling:
    """重複処理のテスト"""

    @pytest.mark.django_db
    def test_skip_duplicate_emails(self, importer, csv_with_duplicates):
        """重複メールアドレスをスキップ"""
        history = importer.import_csv(csv_with_duplicates, skip_duplicates=True)

        # 1行目と2行目は成功、3行目は重複でスキップ
        assert history.success_count == 2
        assert Candidate.objects.count() == 2

    @pytest.mark.django_db
    def test_skip_duplicate_logs_correctly(self, importer, csv_with_duplicates):
        """重複スキップがエラーログに記録される"""
        history = importer.import_csv(csv_with_duplicates, skip_duplicates=True)

        # スキップされた行がログに記録されていること
        skipped = [e for e in history.error_log if e.get('skipped')]
        assert len(skipped) == 1

    @pytest.mark.django_db
    def test_existing_candidate_duplicate(self, importer, tenant, user):
        """既存候補者との重複チェック"""
        # 先に候補者を作成
        Candidate.objects.create(
            tenant=tenant,
            name='既存太郎',
            email='existing@example.com',
            registered_by=user,
        )

        csv = io.StringIO("氏名,メールアドレス\n新規太郎,existing@example.com")
        history = importer.import_csv(csv, skip_duplicates=True)

        # 重複でスキップされること
        assert history.success_count == 0
        skipped = [e for e in history.error_log if e.get('skipped')]
        assert len(skipped) == 1


# =============================================================================
# エンコーディングテスト
# =============================================================================

class TestEncodingHandling:
    """エンコーディング処理のテスト"""

    @pytest.mark.django_db
    def test_utf8_encoding(self, importer, valid_japanese_csv):
        """UTF-8エンコーディング"""
        history = importer.import_csv(valid_japanese_csv, encoding='utf-8')
        assert history.status == ImportHistory.StatusChoices.COMPLETED

    @pytest.mark.django_db
    def test_bytes_content_decode(self, importer):
        """バイトコンテンツのデコード"""
        csv_bytes = "氏名,メールアドレス\n山田太郎,yamada@example.com".encode('utf-8')
        csv_file = io.BytesIO(csv_bytes)
        csv_file.name = 'test.csv'

        history = importer.import_csv(csv_file, encoding='utf-8')
        assert history.success_count == 1

    @pytest.mark.django_db
    def test_shift_jis_encoding(self, importer):
        """Shift-JISエンコーディング"""
        csv_content = "氏名,メールアドレス\n山田太郎,yamada@example.com"
        csv_bytes = csv_content.encode('shift_jis')
        csv_file = io.BytesIO(csv_bytes)
        csv_file.name = 'test.csv'

        history = importer.import_csv(csv_file, encoding='shift_jis')
        assert history.success_count == 1


# =============================================================================
# ドライラン機能テスト
# =============================================================================

class TestDryRunMode:
    """ドライラン機能のテスト"""

    @pytest.mark.django_db
    def test_dry_run_no_candidates_created(self, importer, valid_japanese_csv):
        """ドライランでは候補者が作成されない"""
        initial_count = Candidate.objects.count()

        history = importer.import_csv(valid_japanese_csv, dry_run=True)

        assert history.success_count == 2
        assert Candidate.objects.count() == initial_count

    @pytest.mark.django_db
    def test_dry_run_returns_history(self, importer, valid_japanese_csv):
        """ドライランでも履歴が返される"""
        history = importer.import_csv(valid_japanese_csv, dry_run=True)

        assert history is not None
        assert history.total_rows == 2


# =============================================================================
# バリデーション機能テスト
# =============================================================================

class TestValidateCSV:
    """CSV検証機能のテスト"""

    @pytest.mark.django_db
    def test_validate_valid_csv(self, importer):
        """有効なCSVの検証"""
        csv = io.StringIO("氏名,メールアドレス\n山田太郎,yamada@example.com")
        is_valid, errors = importer.validate_csv(csv)

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.django_db
    def test_validate_missing_required_column(self, importer):
        """必須列が欠けているCSVの検証"""
        csv = io.StringIO("氏名\n山田太郎")  # メールアドレス列がない
        is_valid, errors = importer.validate_csv(csv)

        assert is_valid is False
        assert any('必須列' in str(e.get('error', '')) for e in errors)

    @pytest.mark.django_db
    def test_validate_empty_csv(self, importer):
        """空のCSVの検証"""
        csv = io.StringIO("氏名,メールアドレス")
        is_valid, errors = importer.validate_csv(csv)

        assert is_valid is False
        assert any('データがありません' in str(e.get('error', '')) for e in errors)

    @pytest.mark.django_db
    def test_validate_row_level_errors(self, importer):
        """行レベルのエラー検証"""
        csv = io.StringIO("氏名,メールアドレス\n,yamada@example.com")  # 氏名が空
        is_valid, errors = importer.validate_csv(csv)

        assert is_valid is False
        assert any(e.get('row') == 2 for e in errors)  # 2行目でエラー


# =============================================================================
# テンプレートCSV生成テスト
# =============================================================================

class TestTemplateGeneration:
    """テンプレートCSV生成のテスト"""

    def test_generate_template_csv(self):
        """テンプレートCSV生成"""
        template = CandidateCSVImporter.generate_template_csv()

        assert '氏名' in template
        assert 'メールアドレス' in template
        assert '電話番号' in template
        assert '性別' in template
        assert '生年月日' in template
        assert 'スキル' in template
        assert '資格' in template

    def test_template_includes_sample_data(self):
        """テンプレートにサンプルデータが含まれる"""
        template = CandidateCSVImporter.generate_template_csv()

        assert '山田太郎' in template
        assert 'yamada@example.com' in template


# =============================================================================
# エラーハンドリングテスト
# =============================================================================

class TestErrorHandling:
    """エラーハンドリングのテスト"""

    @pytest.mark.django_db
    def test_import_failure_status(self, importer):
        """全行失敗時のステータス"""
        csv = io.StringIO("氏名,メールアドレス\n,\n,")  # 両方空
        history = importer.import_csv(csv)

        assert history.status == ImportHistory.StatusChoices.FAILED
        assert history.success_count == 0
        assert history.error_count == 2

    @pytest.mark.django_db
    def test_partial_success_status(self, importer):
        """一部成功時のステータス"""
        csv = io.StringIO("氏名,メールアドレス\n山田太郎,yamada@example.com\n,")  # 2行目は失敗
        history = importer.import_csv(csv)

        assert history.status == ImportHistory.StatusChoices.PARTIAL
        assert history.success_count == 1
        assert history.error_count == 1

    @pytest.mark.django_db
    def test_csv_import_error_exception(self):
        """CSVImportErrorの属性テスト"""
        error = CSVImportError(
            message="テストエラー",
            row_number=5,
            field="氏名"
        )

        assert str(error) == "テストエラー"
        assert error.row_number == 5
        assert error.field == "氏名"

    @pytest.mark.django_db
    def test_invalid_encoding_error(self, importer):
        """無効なエンコーディング"""
        # 不正なバイトシーケンス
        csv_bytes = b'\x80\x81invalid'
        csv_file = io.BytesIO(csv_bytes)
        csv_file.name = 'test.csv'

        with pytest.raises(Exception):
            importer.import_csv(csv_file, encoding='utf-8')


# =============================================================================
# ヘッダー検出テスト
# =============================================================================

class TestFieldMappingDetection:
    """フィールドマッピング検出のテスト"""

    @pytest.mark.django_db
    def test_detect_japanese_headers(self, importer):
        """日本語ヘッダーの検出"""
        fieldnames = ['氏名', 'メールアドレス', '電話番号']
        mapping = importer._detect_field_mapping(fieldnames)

        assert mapping == CandidateCSVImporter.DEFAULT_FIELD_MAPPING

    @pytest.mark.django_db
    def test_detect_english_headers(self, importer):
        """英語ヘッダーの検出"""
        fieldnames = ['name', 'email', 'phone']
        mapping = importer._detect_field_mapping(fieldnames)

        assert mapping == CandidateCSVImporter.ENGLISH_FIELD_MAPPING

    @pytest.mark.django_db
    def test_detect_mixed_headers_defaults_to_japanese(self, importer):
        """混在ヘッダーは日本語と判定（氏名が含まれる場合）"""
        fieldnames = ['氏名', 'email', 'phone']
        mapping = importer._detect_field_mapping(fieldnames)

        assert mapping == CandidateCSVImporter.DEFAULT_FIELD_MAPPING

    @pytest.mark.django_db
    def test_detect_empty_fieldnames(self, importer):
        """空のフィールド名はデフォルトマッピング"""
        mapping = importer._detect_field_mapping(None)
        assert mapping == CandidateCSVImporter.DEFAULT_FIELD_MAPPING

        mapping = importer._detect_field_mapping([])
        assert mapping == CandidateCSVImporter.DEFAULT_FIELD_MAPPING


# =============================================================================
# CSVFieldMapping データクラステスト
# =============================================================================

class TestCSVFieldMapping:
    """CSVFieldMappingデータクラスのテスト"""

    def test_field_mapping_defaults(self):
        """デフォルト値のテスト"""
        mapping = CSVFieldMapping(csv_column='test', model_field='test_field')

        assert mapping.required is False
        assert mapping.transform is None

    def test_field_mapping_with_transform(self):
        """変換関数付きマッピング"""
        transform_fn = lambda x: int(x)
        mapping = CSVFieldMapping(
            csv_column='年齢',
            model_field='age',
            required=True,
            transform=transform_fn
        )

        assert mapping.required is True
        assert mapping.transform('10') == 10


# =============================================================================
# カスタムフィールドマッピングテスト
# =============================================================================

class TestCustomFieldMapping:
    """カスタムフィールドマッピングのテスト"""

    @pytest.mark.django_db
    def test_custom_field_mapping(self, tenant, user):
        """カスタムフィールドマッピングの使用"""
        custom_mapping = [
            CSVFieldMapping('名前', 'name', required=True),
            CSVFieldMapping('メール', 'email', required=True),
        ]

        importer = CandidateCSVImporter(
            tenant=tenant,
            user=user,
            field_mapping=custom_mapping
        )

        csv = io.StringIO("名前,メール\n山田太郎,yamada@example.com")
        history = importer.import_csv(csv)

        assert history.success_count == 1
        assert Candidate.objects.filter(email='yamada@example.com').exists()


# =============================================================================
# 大量データテスト（モック）
# =============================================================================

class TestLargeFileHandling:
    """大量データ処理のテスト"""

    @pytest.mark.django_db
    def test_import_100_rows(self, importer):
        """100行のインポート"""
        rows = ["氏名,メールアドレス"]
        for i in range(100):
            rows.append(f"テスト太郎{i},test{i}@example.com")

        csv = io.StringIO("\n".join(rows))
        history = importer.import_csv(csv)

        assert history.total_rows == 100
        assert history.success_count == 100
        assert Candidate.objects.count() == 100

    @pytest.mark.django_db
    def test_import_progress_tracking(self, importer):
        """進捗率の計算"""
        csv = io.StringIO("氏名,メールアドレス\n山田太郎,yamada@example.com\n佐藤花子,sato@example.com")
        history = importer.import_csv(csv)

        assert history.progress_percentage == 100.0


# =============================================================================
# インポート履歴モデルテスト
# =============================================================================

class TestImportHistoryModel:
    """ImportHistoryモデルのテスト"""

    @pytest.mark.django_db
    def test_import_history_str(self, importer, valid_japanese_csv):
        """__str__メソッド"""
        history = importer.import_csv(valid_japanese_csv)

        assert 'unknown.csv' in str(history) or history.file_name in str(history)

    @pytest.mark.django_db
    def test_progress_percentage_zero_total(self, tenant):
        """総行数0の場合の進捗率"""
        history = ImportHistory.objects.create(
            tenant=tenant,
            file_name='test.csv',
            status=ImportHistory.StatusChoices.COMPLETED,
            total_rows=0,
        )

        assert history.progress_percentage == 0

    @pytest.mark.django_db
    def test_status_choices(self):
        """ステータス選択肢"""
        assert ImportHistory.StatusChoices.PENDING == 'pending'
        assert ImportHistory.StatusChoices.PROCESSING == 'processing'
        assert ImportHistory.StatusChoices.COMPLETED == 'completed'
        assert ImportHistory.StatusChoices.FAILED == 'failed'
        assert ImportHistory.StatusChoices.PARTIAL == 'partial'


# =============================================================================
# エッジケーステスト
# =============================================================================

class TestEdgeCases:
    """エッジケースのテスト"""

    @pytest.mark.django_db
    def test_whitespace_only_values(self, importer):
        """空白のみの値"""
        csv = io.StringIO("氏名,メールアドレス\n   ,yamada@example.com")  # 名前が空白のみ
        history = importer.import_csv(csv)

        # 空白のみはエラーになるべき
        assert history.error_count >= 1

    @pytest.mark.django_db
    def test_special_characters_in_name(self, importer):
        """特殊文字を含む名前"""
        csv = io.StringIO("氏名,メールアドレス\n山田<script>alert(1)</script>太郎,yamada@example.com")
        history = importer.import_csv(csv)

        # 特殊文字もそのままインポートされる（XSSはビューレイヤーで対処）
        assert history.success_count == 1

    @pytest.mark.django_db
    def test_very_long_name(self, importer):
        """非常に長い名前"""
        long_name = "山" * 200  # 100文字制限超過
        csv = io.StringIO(f"氏名,メールアドレス\n{long_name},yamada@example.com")

        # データベースエラーになる（max_length=100）
        history = importer.import_csv(csv)
        assert history.error_count >= 1

    @pytest.mark.django_db
    def test_unicode_email(self, importer):
        """日本語ドメインのメールアドレス"""
        csv = io.StringIO("氏名,メールアドレス\n山田太郎,山田@日本.jp")
        history = importer.import_csv(csv)

        # EmailFieldのバリデーションに依存
        assert history.total_rows == 1

    @pytest.mark.django_db
    def test_csv_with_extra_columns(self, importer):
        """余分な列があるCSV"""
        csv = io.StringIO("氏名,メールアドレス,unknown_column,another_column\n山田太郎,yamada@example.com,value1,value2")
        history = importer.import_csv(csv)

        # 余分な列は無視される
        assert history.success_count == 1

    @pytest.mark.django_db
    def test_csv_with_bom(self, importer):
        """BOM付きUTF-8 CSV"""
        csv_content = "\ufeff氏名,メールアドレス\n山田太郎,yamada@example.com"
        csv = io.StringIO(csv_content)
        history = importer.import_csv(csv)

        # BOMがあってもパースできるべき
        assert history.total_rows == 1
