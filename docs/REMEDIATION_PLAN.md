# 技術的負債 対応方針書

**作成日**: 2026-01-04
**ステータス**: 承認待ち

---

## 対応スケジュール概要

| Phase | 対象 | 対応内容 | 影響範囲 |
|-------|------|----------|----------|
| **Phase 1** | セキュリティ | SEC-001〜004 | models, services, views |
| **Phase 2** | アーキテクチャ | ARCH-001〜005 | services, models, managers |
| **Phase 3** | パフォーマンス | PERF-001〜004 | services, views |
| **Phase 4** | コード品質 | CODE-001〜006 | 全体 |

---

## Phase 1: セキュリティ対応

### SEC-001: 認証情報の暗号化

**方針**: django-cryptography を使用してフィールドレベル暗号化

**実装手順**:

1. パッケージインストール
```bash
pip install django-cryptography
```

2. 設定追加
```python
# config/settings/base.py
CRYPTOGRAPHY_KEY = env('CRYPTOGRAPHY_KEY')  # 環境変数から取得
```

3. モデル変更
```python
# apps/settings_app/models.py
from django_cryptography.fields import encrypt

class SpreadsheetConnection(TenantBaseModel):
    # 変更前
    # credentials_json = models.TextField(...)

    # 変更後
    credentials_json = encrypt(models.TextField(
        blank=True,
        verbose_name='認証情報JSON',
    ))
```

4. マイグレーション作成・適用
```bash
python manage.py makemigrations settings_app
python manage.py migrate
```

**影響ファイル**:
- `apps/settings_app/models.py`
- `config/settings/base.py`
- `requirements.txt`

---

### SEC-002: パスワード保存方式の変更

**方針**: スプレッドシートからパスワード列を削除し、初期パスワードはメール送信に変更

**実装手順**:

1. ユーザーシートヘッダーからパスワード列を削除
```python
# apps/core/services/spreadsheet_sync.py

# 変更前
USERS_HEADERS = ['ID', 'メールアドレス', 'パスワード', '姓', '名', ...]

# 変更後
USERS_HEADERS = ['ID', 'メールアドレス', '姓', '名', ...]  # パスワード削除
```

2. push_users() からパスワード処理を削除
```python
def push_users(self):
    for user in users:
        row = [
            str(user.id),
            user.email,
            # user.password_plain は削除
            user.last_name,
            ...
        ]
```

3. pull_users() で新規ユーザー作成時はランダムパスワード生成＋メール送信
```python
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.crypto import get_random_string

def pull_users(self):
    for row in new_users:
        temp_password = get_random_string(12)
        user = CustomUser.objects.create_user(
            email=row['email'],
            password=temp_password,
            ...
        )
        # パスワードリセットメール送信
        self._send_password_setup_email(user)
```

4. パスワードセットアップメール送信機能の追加
```python
def _send_password_setup_email(self, user):
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.SITE_URL}/accounts/password/reset/{user.pk}/{token}/"
    send_mail(
        subject='[Django ATS] アカウントが作成されました',
        message=f'以下のURLからパスワードを設定してください:\n{reset_url}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
```

**影響ファイル**:
- `apps/core/services/spreadsheet_sync.py`
- `apps/accounts/models.py`（メール送信用メソッド追加）
- `templates/emails/password_setup.html`（新規作成）

---

### SEC-003: ログサニタイズ

**方針**: カスタムログフォーマッターでセンシティブ情報をマスク

**実装手順**:

1. カスタムログフィルター作成
```python
# apps/core/logging.py
import logging
import re

class SensitiveDataFilter(logging.Filter):
    """センシティブ情報をマスクするフィルター"""

    PATTERNS = [
        (r'"private_key":\s*"[^"]*"', '"private_key": "***MASKED***"'),
        (r'"client_email":\s*"[^"]*"', '"client_email": "***MASKED***"'),
        (r'password["\']?\s*[:=]\s*["\'][^"\']*["\']', 'password: "***MASKED***"'),
        (r'credentials_json["\']?\s*[:=]\s*["\'][^"\']*["\']', 'credentials_json: "***MASKED***"'),
    ]

    def filter(self, record):
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            for pattern, replacement in self.PATTERNS:
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
            record.msg = msg
        return True
```

2. ログ設定に適用
```python
# config/settings/base.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'sensitive_data': {
            '()': 'apps.core.logging.SensitiveDataFilter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['sensitive_data'],
        },
    },
    ...
}
```

**影響ファイル**:
- `apps/core/logging.py`（新規作成）
- `config/settings/base.py`

---

### SEC-004: CSRF保護の確認・修正

**方針**: 全HTMXリクエストでCSRFトークンを確実に送信

**実装手順**:

1. ベーステンプレートにCSRFヘッダー設定
```html
<!-- templates/base.html -->
<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
```

2. JavaScriptでのCSRF設定（HTMX初期化時）
```html
<!-- templates/base.html -->
<script>
document.body.addEventListener('htmx:configRequest', (event) => {
    event.detail.headers['X-CSRFToken'] = '{{ csrf_token }}';
});
</script>
```

3. 各テンプレートの確認・修正
```bash
# 確認コマンド
grep -r "hx-post\|hx-put\|hx-delete" templates/
# 各箇所でCSRFトークンが送信されることを確認
```

**影響ファイル**:
- `templates/base.html`
- 全HTMXを使用するテンプレート（確認のみ）

---

## Phase 2: アーキテクチャ対応

### ARCH-001: データソース設計の明確化

**方針**: PostgreSQLを「Single Source of Truth」とし、Spreadsheetは「同期ビュー」と位置づけ

**実装手順**:

1. 設計ドキュメント更新
```markdown
# データソース設計
- **Master**: PostgreSQL（常に正）
- **Replica**: Google Spreadsheet（読み取り用ビュー）
- **同期方向**: 原則 DB → Spreadsheet（push）
- **例外**: ユーザー一括登録時のみ Spreadsheet → DB（pull）
```

2. 同期方向を明示する定数追加
```python
# apps/core/constants.py
class SyncDirection:
    PUSH = 'push'  # DB → Spreadsheet
    PULL = 'pull'  # Spreadsheet → DB

class SyncPolicy:
    CANDIDATES = SyncDirection.PUSH  # 候補者は常にpush
    USERS = 'bidirectional'  # ユーザーは双方向
```

3. 競合検出の実装
```python
# apps/core/services/spreadsheet_sync.py
def detect_conflicts(self, entity_type: str) -> list:
    """DBとSpreadsheetの差分を検出"""
    db_data = self._get_db_data(entity_type)
    sheet_data = self._get_sheet_data(entity_type)

    conflicts = []
    for db_row in db_data:
        sheet_row = sheet_data.get(db_row['id'])
        if sheet_row and db_row['updated_at'] != sheet_row.get('updated_at'):
            conflicts.append({
                'id': db_row['id'],
                'db_updated_at': db_row['updated_at'],
                'sheet_updated_at': sheet_row.get('updated_at'),
            })
    return conflicts
```

**影響ファイル**:
- `apps/core/constants.py`
- `apps/core/services/spreadsheet_sync.py`
- `docs/SYSTEM_ARCHITECTURE.md`

---

### ARCH-002: 同期処理のトランザクション対応

**方針**: DB操作はDjangoトランザクション、Spreadsheet操作は補償トランザクション

**実装手順**:

1. トランザクション対応の同期メソッド
```python
# apps/core/services/spreadsheet_sync.py
from django.db import transaction

class SpreadsheetSyncService:

    def sync_all(self) -> dict:
        """全エンティティを同期（トランザクション対応）"""
        results = {}
        rollback_actions = []

        try:
            with transaction.atomic():
                # DB側の処理
                results['candidates'] = self._sync_candidates_db()
                rollback_actions.append(('candidates', self._rollback_candidates))

                results['applications'] = self._sync_applications_db()
                rollback_actions.append(('applications', self._rollback_applications))

            # Spreadsheet側の処理（DB成功後）
            for entity in ['candidates', 'applications']:
                self._push_to_sheet(entity)

        except Exception as e:
            # Spreadsheet側のロールバック
            for entity, rollback_fn in rollback_actions:
                try:
                    rollback_fn()
                except Exception:
                    pass  # ロールバック失敗はログのみ
            raise

        return results
```

2. 同期履歴テーブル追加
```python
# apps/core/models.py
class SyncHistory(BaseModel):
    """同期履歴"""
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    entity_type = models.CharField(max_length=50)
    direction = models.CharField(max_length=10)  # push/pull
    status = models.CharField(max_length=20)  # success/failed/partial
    records_processed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True)
```

**影響ファイル**:
- `apps/core/services/spreadsheet_sync.py`
- `apps/core/models.py`
- マイグレーションファイル

---

### ARCH-003: pull_*メソッドの完成

**方針**: applications, interviews の pull メソッドを実装

**実装手順**:

1. pull_applications() 実装
```python
def pull_applications(self) -> dict:
    """Spreadsheet → DB: 応募データ同期"""
    worksheet = self._get_or_create_sheet('応募')
    rows = worksheet.get_all_records()

    created, updated, errors = 0, 0, []

    for row in rows:
        try:
            candidate = Candidate.objects.get(id=row['候補者ID'])
            job = Job.objects.get(id=row['求人ID'])

            application, is_new = Application.objects.update_or_create(
                id=row.get('ID') or None,
                defaults={
                    'tenant': self.tenant,
                    'candidate': candidate,
                    'job': job,
                    'status': self._map_status(row['ステータス']),
                    'applied_at': parse_date(row['応募日']),
                }
            )
            if is_new:
                created += 1
            else:
                updated += 1
        except Exception as e:
            errors.append({'row': row, 'error': str(e)})

    return {
        'success': len(errors) == 0,
        'created': created,
        'updated': updated,
        'errors': errors,
    }
```

2. pull_interviews() 実装（同様のパターン）

**影響ファイル**:
- `apps/core/services/spreadsheet_sync.py`

---

### ARCH-004: シート定義の外部化

**方針**: シート構造をデータベースで管理し、テナントごとのカスタマイズを可能に

**実装手順**:

1. シート定義モデル追加
```python
# apps/settings_app/models.py
class SheetDefinition(TenantBaseModel):
    """スプレッドシートシート定義"""
    entity_type = models.CharField(max_length=50)  # candidates, applications, etc.
    sheet_name = models.CharField(max_length=100)
    headers = models.JSONField()  # ['ID', '姓', '名', ...]
    column_mapping = models.JSONField()  # {'id': 'ID', 'last_name': '姓', ...}
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['tenant', 'entity_type']
```

2. デフォルト定義のシーダー作成
```python
# apps/settings_app/management/commands/seed_sheet_definitions.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        defaults = [
            {
                'entity_type': 'candidates',
                'sheet_name': '候補者',
                'headers': ['ID', '姓', '名', 'メール', '電話番号', ...],
                'column_mapping': {
                    'id': 'ID',
                    'last_name': '姓',
                    ...
                }
            },
            ...
        ]
        for tenant in Tenant.objects.all():
            for definition in defaults:
                SheetDefinition.objects.get_or_create(
                    tenant=tenant,
                    entity_type=definition['entity_type'],
                    defaults=definition
                )
```

3. SpreadsheetSyncServiceを定義参照に変更
```python
def _get_sheet_definition(self, entity_type: str) -> SheetDefinition:
    return SheetDefinition.objects.get(
        tenant=self.tenant,
        entity_type=entity_type,
        is_active=True
    )
```

**影響ファイル**:
- `apps/settings_app/models.py`
- `apps/core/services/spreadsheet_sync.py`
- マイグレーションファイル

---

### ARCH-005: テナント分離の強化

**方針**: カスタムManagerでクエリセット自動フィルタリング

**実装手順**:

1. テナントコンテキスト管理
```python
# apps/core/context.py
from contextvars import ContextVar
from typing import Optional

_current_tenant: ContextVar[Optional['Tenant']] = ContextVar('current_tenant', default=None)

def get_current_tenant():
    return _current_tenant.get()

def set_current_tenant(tenant):
    _current_tenant.set(tenant)
```

2. カスタムManager作成
```python
# apps/core/managers.py
from django.db import models
from apps.core.context import get_current_tenant

class TenantManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        tenant = get_current_tenant()
        if tenant:
            return qs.filter(tenant=tenant)
        return qs

class TenantBaseModel(BaseModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)

    objects = TenantManager()
    all_objects = models.Manager()  # テナントフィルタなし

    class Meta:
        abstract = True
```

3. ミドルウェア更新
```python
# apps/core/middleware.py
from apps.core.context import set_current_tenant

class TenantMiddleware:
    def __call__(self, request):
        if request.user.is_authenticated and request.user.tenant:
            set_current_tenant(request.user.tenant)
        response = self.get_response(request)
        set_current_tenant(None)
        return response
```

**影響ファイル**:
- `apps/core/context.py`（新規作成）
- `apps/core/managers.py`（新規作成）
- `apps/core/models.py`
- `apps/core/middleware.py`

---

## Phase 3: パフォーマンス対応

### PERF-001: 差分同期の実装

**方針**: 最終同期日時以降に更新されたレコードのみ同期

**実装手順**:

1. 差分同期メソッド追加
```python
def push_candidates_incremental(self) -> dict:
    """差分同期: 更新分のみプッシュ"""
    last_sync = self.spreadsheet.last_synced_at

    if last_sync:
        candidates = Candidate.objects.filter(
            tenant=self.tenant,
            updated_at__gt=last_sync
        )
    else:
        # 初回は全件
        return self.push_candidates()

    worksheet = self._get_or_create_sheet('候補者')
    existing_ids = self._get_existing_ids(worksheet)

    updates = []
    for candidate in candidates:
        row_index = existing_ids.get(str(candidate.id))
        if row_index:
            # 更新
            updates.append({
                'range': f'A{row_index}:Z{row_index}',
                'values': [self._candidate_to_row(candidate)]
            })
        else:
            # 追加
            worksheet.append_row(self._candidate_to_row(candidate))

    if updates:
        worksheet.batch_update(updates)

    return {'success': True, 'updated': len(updates)}
```

**影響ファイル**:
- `apps/core/services/spreadsheet_sync.py`

---

### PERF-002: N+1クエリの解消

**方針**: annotate/select_relatedで一括取得

**実装手順**:

1. TenantDetailView修正
```python
# apps/tenants/views.py
from django.db.models import Count

class TenantDetailView(SuperuserRequiredMixin, DetailView):
    def get_queryset(self):
        return Tenant.objects.annotate(
            job_count=Count('job_set'),
            candidate_count=Count('candidate_set'),
            application_count=Count('application_set'),
            interview_count=Count('interview_set'),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.object

        context['stats'] = {
            'jobs': tenant.job_count,
            'candidates': tenant.candidate_count,
            'applications': tenant.application_count,
            'interviews': tenant.interview_count,
        }
        return context
```

2. 他のListViewも同様に最適化

**影響ファイル**:
- `apps/tenants/views.py`
- `apps/jobs/views.py`
- `apps/candidates/views.py`

---

### PERF-003/004: 接続キャッシュ・プーリング

**方針**: gspread接続をキャッシュ

**実装手順**:

```python
# apps/core/services/spreadsheet_sync.py
from functools import lru_cache
import gspread

class SpreadsheetSyncService:
    _client_cache = {}

    @classmethod
    def _get_client(cls, credentials_json: str) -> gspread.Client:
        """認証済みクライアントをキャッシュ"""
        cache_key = hash(credentials_json)
        if cache_key not in cls._client_cache:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                json.loads(credentials_json),
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            cls._client_cache[cache_key] = gspread.authorize(creds)
        return cls._client_cache[cache_key]
```

**影響ファイル**:
- `apps/core/services/spreadsheet_sync.py`

---

## Phase 4: コード品質対応

### CODE-001: 共通バリデータの集約

**実装**:
```python
# apps/core/validators.py
import re
from django.core.exceptions import ValidationError

def validate_phone_number(value):
    pattern = r'^[\d\-]+$'
    if not re.match(pattern, value):
        raise ValidationError('電話番号の形式が正しくありません')

def validate_postal_code(value):
    pattern = r'^\d{3}-?\d{4}$'
    if not re.match(pattern, value):
        raise ValidationError('郵便番号の形式が正しくありません')
```

---

### CODE-002: 定数の集約

**実装**:
```python
# apps/core/constants.py
class Pagination:
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

class SyncLimits:
    MAX_ROWS_PER_BATCH = 1000
    API_RATE_LIMIT = 100  # requests per 100 seconds
```

---

### CODE-003: カスタム例外クラス

**実装**:
```python
# apps/core/exceptions.py
class SpreadsheetSyncError(Exception):
    """スプレッドシート同期エラー"""
    pass

class TenantNotFoundError(Exception):
    """テナント未設定エラー"""
    pass

class ConflictError(Exception):
    """データ競合エラー"""
    pass
```

---

### CODE-004: テストカバレッジ向上

**方針**:
1. pytest-cov導入
2. カバレッジ80%目標
3. CI/CDでチェック

```bash
# requirements-dev.txt に追加
pytest-cov==4.1.0
```

```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    pytest --cov=apps --cov-report=xml --cov-fail-under=80
```

---

### CODE-005: docstring追加

**方針**: Google Style docstringを使用

```python
def push_candidates(self) -> dict:
    """候補者データをスプレッドシートにプッシュする。

    DBの候補者データをGoogle Spreadsheetに同期します。
    既存データは全て上書きされます。

    Returns:
        dict: 同期結果
            - success (bool): 成功/失敗
            - count (int): 同期件数
            - error (str, optional): エラーメッセージ

    Raises:
        SpreadsheetSyncError: 同期処理に失敗した場合
    """
```

---

### CODE-006: デッドコード除去

**方針**: vulture + 手動レビュー

```bash
pip install vulture
vulture apps/ --min-confidence 80
```

---

## 実装順序（推奨）

### 週1: セキュリティ緊急対応
1. SEC-001: 認証情報暗号化
2. SEC-002: パスワード保存廃止

### 週2: セキュリティ完了 + アーキテクチャ開始
3. SEC-003: ログサニタイズ
4. SEC-004: CSRF確認
5. ARCH-001: データソース設計明確化

### 週3: アーキテクチャ
6. ARCH-002: トランザクション対応
7. ARCH-003: pullメソッド完成
8. ARCH-005: テナント分離強化

### 週4: アーキテクチャ完了 + パフォーマンス
9. ARCH-004: シート定義外部化
10. PERF-001: 差分同期
11. PERF-002: N+1解消

### 週5: コード品質
12. CODE-001〜006: 全項目

---

## 承認

この対応方針で進めてよろしいでしょうか？

- [ ] 承認
- [ ] 修正依頼（内容: ）
