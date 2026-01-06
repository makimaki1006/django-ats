# 技術的負債・設計課題分析レポート

**作成日**: 2026-01-04
**対象**: Django ATS v1.0
**分析者**: Claude Code

---

## 概要

本ドキュメントは、Django ATSプロジェクトにおける技術的負債、設計上の課題、および一般的なベストプラクティスからの乖離を分析したものです。

### 評価サマリー

| カテゴリ | 深刻度 | 項目数 |
|---------|--------|--------|
| 🔴 セキュリティ | Critical | 4 |
| 🟠 アーキテクチャ | High | 5 |
| 🟡 パフォーマンス | Medium | 4 |
| 🟢 コード品質 | Low | 6 |

---

## 🔴 セキュリティ課題（Critical）

### SEC-001: Google認証情報の平文保存

**場所**: `apps/settings_app/models.py:SpreadsheetConnection.credentials_json`

**現状**:
```python
credentials_json = models.TextField(
    blank=True,
    verbose_name='認証情報JSON',
    help_text='Google Cloud サービスアカウントの認証情報（JSON形式）'
)
```

**問題点**:
- サービスアカウントの秘密鍵がデータベースに平文で保存されている
- DBダンプやバックアップから認証情報が漏洩するリスク

**推奨対策**:
1. Django-Fernet-Fields等で暗号化フィールドを使用
2. AWS Secrets Manager/HashiCorp Vault等のシークレット管理サービスを利用
3. 環境変数経由でファイルパスのみ保存

**優先度**: 🔴 Critical（本番デプロイ前に必須）

---

### SEC-002: スプレッドシートにパスワード保存

**場所**: `apps/core/services/spreadsheet_sync.py:789-815`

**現状**:
```python
def _create_users_sheet(self, spreadsheet, sheet_name: str = 'ユーザー'):
    headers = [
        'ID', 'メールアドレス', 'パスワード', '姓', '名', ...
    ]
```

**問題点**:
- ユーザーパスワードがGoogle Spreadsheetに平文で保存される
- スプレッドシートの共有設定次第で第三者にパスワードが漏洩
- Googleのアクセスログに残る可能性

**推奨対策**:
1. パスワード列を削除し、初期パスワードはメール送信に変更
2. どうしても必要な場合は一方向ハッシュ化して保存
3. スプレッドシートからのユーザー作成後、パスワード列をクリア

**優先度**: 🔴 Critical

---

### SEC-003: 認証情報のログ出力リスク

**場所**: `apps/core/services/spreadsheet_sync.py` 全体

**現状**:
- エラーハンドリング時に `credentials_json` を含むオブジェクトがログに出力される可能性

**推奨対策**:
1. カスタム例外クラスで認証情報をマスク
2. logging設定でセンシティブデータをフィルタリング

**優先度**: 🟠 High

---

### SEC-004: CSRF保護の不完全な適用

**場所**: `apps/tenants/views.py` のHTMX対応ビュー

**現状**:
- 一部のPOSTエンドポイントでCSRF検証が適切に行われているか要確認
- HTMXリクエストでの `hx-headers` によるCSRFトークン送信の一貫性

**推奨対策**:
1. 全HTMXリクエストで `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` を確認
2. Django CSRF middleware設定の見直し

**優先度**: 🟠 High

---

## 🟠 アーキテクチャ課題（High）

### ARCH-001: PostgreSQL/Spreadsheet二重データソース

**場所**: システム全体

**現状**:
```
PostgreSQL                    Google Spreadsheet
├── candidates                ├── 候補者シート
├── applications              ├── 応募シート
├── interviews                ├── 面接シート
└── users                     └── ユーザーシート
```

**問題点**:
- 同一データが2箇所に存在し、どちらが「真実の源」か不明確
- 同時編集時の競合解決ロジックがない
- 整合性が保証されない

**推奨対策**:
1. **Single Source of Truth原則**: PostgreSQLを正とし、Spreadsheetは読み取り専用ビュー
2. **競合解決ポリシー**: `version`フィールドを活用した楽観的ロック
3. **監査ログ**: 同期履歴の記録と差分検知

**影響度**: データ整合性に直接影響

---

### ARCH-002: 同期の非原子性

**場所**: `apps/core/services/spreadsheet_sync.py:sync_all()`

**現状**:
```python
def sync_all(self) -> dict:
    results = {}
    results['candidates'] = self.push_candidates()  # 成功
    results['applications'] = self.push_applications()  # 失敗したら？
    # ... 以降の処理は実行されるが、候補者は既にpush済み
```

**問題点**:
- 途中で失敗しても前の処理はロールバックされない
- 部分的に更新された状態が残る

**推奨対策**:
```python
from django.db import transaction

def sync_all(self) -> dict:
    with transaction.atomic():
        # DB側のトランザクション
        ...
    # Spreadsheet側は補償トランザクションパターンで対応
```

**優先度**: 🟠 High

---

### ARCH-003: 同期方向の不明確さ

**場所**: `apps/core/services/spreadsheet_sync.py`

**現状**:
- `push_*()` メソッド: DB → Spreadsheet（実装済み）
- `pull_*()` メソッド: Spreadsheet → DB（一部のみ実装）

```python
def pull_applications(self):
    # TODO: Implement application pull logic
    pass

def pull_interviews(self):
    # TODO: Implement interview pull logic
    pass
```

**問題点**:
- 双方向同期が不完全
- どちらの方向が主かが設計上不明確

**推奨対策**:
1. 同期方向を設計ドキュメントで明確化
2. 未実装メソッドの完成または削除
3. 同期モード（push-only, pull-only, bidirectional）の設定可能化

**優先度**: 🟠 High

---

### ARCH-004: ハードコードされたシート構造

**場所**: `apps/core/services/spreadsheet_sync.py:649-720`

**現状**:
```python
SHEET_DEFINITIONS = {
    'candidates': {
        'name': '候補者',
        'headers': ['ID', '姓', '名', 'メール', ...]
    },
    ...
}
```

**問題点**:
- シート構造がコードにハードコード
- カラム追加・変更時にコード修正が必要
- テナントごとのカスタマイズ不可

**推奨対策**:
1. シート定義をデータベース/設定ファイルに外出し
2. マイグレーション機構の導入（シート構造変更時）
3. バージョン管理（シート構造のバージョンフィールド）

**優先度**: 🟡 Medium

---

### ARCH-005: テナント分離の不完全性

**場所**: `apps/core/models.py:TenantBaseModel`

**現状**:
```python
class TenantBaseModel(BaseModel):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)s_set'
    )
```

**問題点**:
- クエリセットのフィルタリングがView層に依存
- ミドルウェアでのテナント設定が不完全な場合、データ漏洩リスク
- 管理画面（Django Admin）でのテナント分離が未実装

**推奨対策**:
1. カスタムManagerでデフォルトフィルタリング
```python
class TenantManager(models.Manager):
    def get_queryset(self):
        tenant = get_current_tenant()
        return super().get_queryset().filter(tenant=tenant)
```
2. Django Admin用のテナントフィルタリング追加

**優先度**: 🟠 High

---

## 🟡 パフォーマンス課題（Medium）

### PERF-001: 非効率な全シート書き換え

**場所**: `apps/core/services/spreadsheet_sync.py:push_candidates()`

**現状**:
```python
def push_candidates(self):
    worksheet.clear()  # 全削除
    worksheet.update('A1', [headers] + data)  # 全書き込み
```

**問題点**:
- 1件の変更でも全データを再書き込み
- API呼び出し回数が多く、レート制限に達しやすい
- 大量データ時のパフォーマンス低下

**推奨対策**:
1. 差分更新の実装
```python
def push_candidates_incremental(self):
    existing = self._get_existing_ids(worksheet)
    to_update = candidates.filter(updated_at__gt=last_sync)
    to_create = candidates.exclude(id__in=existing)
    # 差分のみ更新
```
2. バッチ更新APIの活用（`batch_update`）

**影響**: Google Sheets API制限（100リクエスト/100秒）

---

### PERF-002: N+1クエリ問題

**場所**: `apps/tenants/views.py:TenantDetailView`

**現状**:
```python
def get_context_data(self, **kwargs):
    context['stats'] = {
        'jobs': Job.objects.filter(tenant=tenant).count(),
        'candidates': Candidate.objects.filter(tenant=tenant).count(),
        'applications': Application.objects.filter(tenant=tenant).count(),
        'interviews': Interview.objects.filter(tenant=tenant).count(),
    }
```

**問題点**:
- 4回の個別クエリ
- テナント詳細表示のたびに実行

**推奨対策**:
```python
from django.db.models import Count

stats = Tenant.objects.filter(pk=tenant.pk).annotate(
    job_count=Count('job_set'),
    candidate_count=Count('candidate_set'),
    ...
).first()
```

**優先度**: 🟡 Medium

---

### PERF-003: ジオコーディングキャッシュなし

**場所**: 該当なし（未実装）

**推奨対策**:
- Google Maps APIのジオコーディング結果をキャッシュ
- Redis/Memcachedの導入検討

**優先度**: 🟢 Low（機能未使用の場合）

---

### PERF-004: スプレッドシート接続の再利用なし

**場所**: `apps/core/services/spreadsheet_sync.py`

**現状**:
```python
def __init__(self, spreadsheet: TenantSpreadsheet):
    self.connection = SpreadsheetConnection.objects.filter(...).first()
    # 毎回認証処理が走る
```

**推奨対策**:
1. 接続プーリング
2. 認証トークンのキャッシュ
3. シングルトンパターンでの接続管理

**優先度**: 🟡 Medium

---

## 🟢 コード品質課題（Low）

### CODE-001: 重複するバリデーションロジック

**場所**: 複数のforms.py

**現状**:
- メールアドレス検証が複数箇所で実装
- 電話番号フォーマット検証の重複

**推奨対策**:
- `apps/core/validators.py` に共通バリデータを集約
- ModelFieldレベルでのバリデータ設定

---

### CODE-002: マジックナンバー/マジックストリング

**場所**: 各所

**現状**:
```python
if user.role == 'system_admin':  # マジックストリング
    ...
if page_size > 100:  # マジックナンバー
    ...
```

**推奨対策**:
- `apps/core/constants.py` に定数を集約
- Enumクラスの活用

---

### CODE-003: エラーハンドリングの不統一

**場所**: `apps/core/services/spreadsheet_sync.py`

**現状**:
```python
try:
    ...
except Exception as e:
    return {'success': False, 'error': str(e)}
```

**問題点**:
- 全例外をキャッチしており、デバッグが困難
- エラーメッセージが日本語/英語混在

**推奨対策**:
1. カスタム例外クラスの定義
2. 例外の種類に応じた適切なハンドリング
3. エラーメッセージの国際化（i18n）

---

### CODE-004: テストカバレッジの偏り

**場所**: `apps/*/tests/`

**現状**:
- モデルテスト: 充実
- ビューテスト: 不足
- サービステスト: 不足
- E2Eテスト: 未実装

**推奨対策**:
1. pytest-cov でカバレッジ計測
2. 目標カバレッジ: 80%以上
3. CI/CDでのカバレッジチェック

---

### CODE-005: ドキュメント/コメントの不足

**場所**: 全体

**現状**:
- docstringが一部メソッドで欠落
- 複雑なロジックの説明コメントなし
- API仕様書なし

**推奨対策**:
1. Sphinxによるドキュメント自動生成
2. OpenAPI/Swagger仕様書の作成
3. コーディング規約の策定

---

### CODE-006: 未使用コード/デッドコード

**場所**: 要調査

**推奨対策**:
1. `vulture` ツールでデッドコード検出
2. 定期的なコードレビュー

---

## 対応優先度マトリクス

```
影響度
  高 │  SEC-001   SEC-002   ARCH-001
     │  ARCH-002  ARCH-005
  中 │  SEC-003   SEC-004   ARCH-003
     │  PERF-001  PERF-002
  低 │  ARCH-004  PERF-003  PERF-004
     │  CODE-*
     └────────────────────────────────
           低      中      高   緊急度
```

## 推奨対応順序

### Phase 1: セキュリティ（本番前必須）
1. SEC-001: 認証情報の暗号化
2. SEC-002: パスワードのスプレッドシート保存廃止
3. SEC-003: ログのサニタイズ

### Phase 2: アーキテクチャ安定化
4. ARCH-001: Single Source of Truth設計
5. ARCH-002: トランザクション対応
6. ARCH-005: テナント分離強化

### Phase 3: パフォーマンス最適化
7. PERF-001: 差分同期実装
8. PERF-002: N+1クエリ解消

### Phase 4: コード品質向上
9. CODE-001〜006: リファクタリング
10. テストカバレッジ向上

---

## 参考資料

- [OWASP Top 10](https://owasp.org/Top10/)
- [Django Security Best Practices](https://docs.djangoproject.com/en/5.0/topics/security/)
- [12 Factor App](https://12factor.net/)
- [Google Sheets API Best Practices](https://developers.google.com/sheets/api/guides/concepts)
