# Django ATS 移行計画書

作成日: 2025-12-24
更新日: 2025-12-24 (設計負債・技術負債・不測の事態対策追加)
ステータス: 計画中

---

## 1. 概要

### 1.1 目的
Reflex ATS (採用管理システム) を Django + htmx + Tailwind CSS へ完全移行する。

### 1.2 移行理由
- Reflexの制限 (FitGap分析: 46点)
  - ロール権限管理が困難
  - デプロイの不安定性
  - DBマイグレーションの手動管理
  - Var型の制限
- Djangoの利点 (FitGap分析: 93点)
  - 認証・権限が標準装備
  - 本番実績多数
  - デプロイ安定
  - htmxでモダンUI可能

### 1.3 スコープ
- 全14テーブルの移行
- 全20画面の移行
- 全4ロールの権限管理
- Supabase PostgreSQLの継続利用 (オプション)

---

## 2. 現状分析

### 2.1 既存システム構成 (Reflex ATS)

```
reflex_ats/
├── reflex_ats.py          # エントリーポイント (159行)
├── auth_state.py          # 認証State
├── *_state.py             # 各機能State (13ファイル)
├── pages/                 # 18ページ
├── components/            # 共通コンポーネント
└── utils/                 # ユーティリティ
```

### 2.2 データベース (Supabase PostgreSQL)

| テーブル | レコード数 (推定) | 備考 |
|----------|-------------------|------|
| tenants | 2-10 | テスト用 |
| profiles | 10-50 | ユーザー |
| candidates | 100-500 | 候補者 |
| applications | 200-1000 | 応募 |
| jobs | 20-100 | 求人 |
| その他 | 各10-100 | - |

### 2.3 移行対象機能

| 機能カテゴリ | 機能数 | 優先度 |
|--------------|--------|--------|
| 認証・ユーザー管理 | 7 | 必須 |
| テナント管理 | 4 | 必須 |
| 応募者管理 | 8 | 必須 |
| 求人票管理 | 6 | 必須 |
| ペルソナ管理 | 5 | 必須 |
| エージェント管理 | 10 | 必須 |
| 面接管理 | 5 | 必須 |
| 通知機能 | 5 | 中 |
| ダッシュボード | 5 | 中 |
| 設定機能 | 3 | 中 |

---

## 3. 技術設計

### 3.1 技術スタック

| 項目 | 技術 | バージョン |
|------|------|------------|
| フレームワーク | Django | 5.0.x |
| Python | Python | 3.11+ |
| 認証 | django-allauth | 0.61+ |
| 権限管理 | django-guardian | 2.4+ |
| UI拡張 | django-htmx | 1.17+ |
| CSS | Tailwind CSS | 3.4+ |
| フォーム | django-crispy-forms | 2.1+ |
| フィルタ | django-filter | 24.1+ |
| テスト | pytest-django | 4.8+ |
| DB | PostgreSQL | 15+ |
| バックグラウンドジョブ | Celery + Redis | 5.3+ |
| エラー追跡 | Sentry | 最新 |

### 3.2 ディレクトリ構成

```
django_ats/
├── manage.py
├── requirements.txt
├── pytest.ini
├── tailwind.config.js
├── package.json
│
├── config/                    # プロジェクト設定
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py           # 共通設定
│   │   ├── development.py    # 開発環境
│   │   └── production.py     # 本番環境
│   ├── urls.py               # ルートURL
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                      # Djangoアプリ
│   ├── __init__.py
│   │
│   ├── core/                  # 共通機能
│   │   ├── models.py         # BaseModel
│   │   ├── mixins.py         # TenantMixin
│   │   ├── middleware.py     # TenantMiddleware
│   │   ├── exceptions.py     # カスタム例外
│   │   ├── error_handlers.py # グローバルエラーハンドラー
│   │   └── templatetags/
│   │
│   ├── accounts/              # 認証・ユーザー
│   │   ├── models.py         # CustomUser, Profile
│   │   ├── views.py
│   │   ├── forms.py
│   │   └── urls.py
│   │
│   ├── tenants/               # テナント管理
│   │   ├── models.py         # Tenant
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── candidates/            # 候補者管理
│   │   ├── models.py         # Candidate
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── services.py       # CSVインポート/エクスポート
│   │   └── urls.py
│   │
│   ├── applications/          # 応募管理
│   │   ├── models.py         # Application, StatusHistory
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── jobs/                  # 求人管理
│   │   ├── models.py         # Job, JobPersona, JobAgentCompany
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── interviews/            # 面接管理
│   │   ├── models.py         # Interview
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── personas/              # ペルソナ管理
│   │   ├── models.py         # Persona
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── agents/                # エージェント管理
│   │   ├── models.py         # AgentCompany
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── notifications/         # 通知
│   │   ├── models.py         # Notification
│   │   ├── views.py
│   │   ├── signals.py        # 通知シグナル
│   │   └── urls.py
│   │
│   ├── reports/               # レポート
│   │   ├── views.py
│   │   └── urls.py
│   │
│   └── settings_app/          # 設定機能
│       ├── models.py         # StatusSetting, ApplicationSource
│       ├── views.py
│       └── urls.py
│
├── templates/                 # テンプレート
│   ├── base.html             # ベーステンプレート
│   ├── errors/               # エラーページ
│   │   ├── 400.html
│   │   ├── 403.html
│   │   ├── 404.html
│   │   ├── 500.html
│   │   └── maintenance.html
│   ├── components/           # 再利用コンポーネント
│   │   ├── sidebar.html
│   │   ├── navbar.html
│   │   ├── modal.html
│   │   ├── table.html
│   │   └── forms/
│   └── [各アプリ用テンプレート]
│
├── static/                    # 静的ファイル
│   ├── css/
│   │   └── output.css        # Tailwind出力
│   ├── js/
│   │   └── htmx.min.js
│   └── images/
│
└── tests/                     # テスト
    ├── conftest.py
    ├── factories.py          # テストデータファクトリ
    ├── test_accounts/
    ├── test_candidates/
    ├── test_applications/
    ├── test_jobs/
    ├── test_security/        # セキュリティテスト
    └── test_integration/
```

### 3.3 データベースモデル設計

#### 3.3.1 BaseModel (共通)

```python
# apps/core/models.py
from django.db import models
import uuid

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)  # 楽観的ロック用

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # 楽観的ロック: 更新時にversionをインクリメント
        if self.pk:
            self.version += 1
        super().save(*args, **kwargs)


class TenantBaseModel(BaseModel):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)ss'
    )

    class Meta:
        abstract = True
```

#### 3.3.2 主要モデル

| モデル | 継承 | 主要フィールド | 設計負債対策 |
|--------|------|----------------|--------------|
| Tenant | BaseModel | name, logo_url, settings | - |
| CustomUser | AbstractUser | email, tenant, role | - |
| Profile | TenantBaseModel | user, display_name, agent_company | - |
| AgentCompany | BaseModel | name, contact_email, is_active | マスタ管理 |
| Candidate | TenantBaseModel | name, email, phone, agent_company | - |
| Application | TenantBaseModel | candidate, job, status, source | version追加 |
| Job | TenantBaseModel | title, unique_code, status | - |
| Persona | TenantBaseModel | name, description, skills | CRUD機能 |
| Interview | TenantBaseModel | application, scheduled_at, status | - |
| Notification | TenantBaseModel | user, type, title, is_read | シグナル連携 |
| StatusSetting | TenantBaseModel | name, display_order, category | - |
| ApplicationSource | BaseModel | name, type, tenant (nullable) | - |
| ImportHistory | TenantBaseModel | file_name, status, error_log | CSVインポート履歴 |

### 3.4 認証・権限設計

#### 3.4.1 ロール定義

```python
# apps/accounts/models.py
class UserRole(models.TextChoices):
    SYSTEM_ADMIN = 'system_admin', 'システム管理者'
    CLIENT_ADMIN = 'client_admin', '企業管理者'
    CLIENT_RECRUITER = 'client_recruiter', '企業担当者'
    AGENT = 'agent', 'エージェント'
```

#### 3.4.2 権限マトリクス

| 権限 | system_admin | client_admin | client_recruiter | agent |
|------|:------------:|:------------:|:----------------:|:-----:|
| テナント横断 | O | - | - | - |
| テナント設定 | O | O | - | - |
| ユーザー招待 | O | O | - | - |
| 応募者登録 | O | O | O | O(自社) |
| 応募者編集 | O | O | O | - |
| 求人管理 | O | O | O | -(閲覧) |
| レポート | O | O | O | - |

#### 3.4.3 Mixinによる権限チェック

```python
# apps/core/mixins.py
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class TenantAccessMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if user.role == 'system_admin':
            return True
        return user.tenant_id == self.get_object().tenant_id

    def handle_no_permission(self):
        raise PermissionDenied("他テナントのデータにはアクセスできません")

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role in ['system_admin', 'client_admin']

class OptimisticLockMixin:
    """楽観的ロックによる同時編集コンフリクト対策"""
    def form_valid(self, form):
        obj = form.instance
        if hasattr(obj, 'version'):
            current_version = self.get_object().version
            if obj.version != current_version:
                form.add_error(None, "他のユーザーが編集中です。再読み込みしてください。")
                return self.form_invalid(form)
        return super().form_valid(form)
```

### 3.5 URL設計

| URL | View | 説明 |
|-----|------|------|
| / | LoginView | ログイン |
| /signup/ | SignupView | 新規登録 |
| /dashboard/ | DashboardView | ダッシュボード |
| /candidates/ | CandidateListView | 候補者一覧 |
| /candidates/<uuid:pk>/ | CandidateDetailView | 候補者詳細 |
| /candidates/create/ | CandidateCreateView | 候補者登録 |
| /candidates/import/ | CandidateImportView | CSVインポート |
| /candidates/export/ | CandidateExportView | CSVエクスポート |
| /applications/ | ApplicationListView | 応募一覧 |
| /jobs/ | JobListView | 求人一覧 |
| /jobs/<uuid:pk>/ | JobDetailView | 求人詳細 |
| /jobs/<uuid:pk>/duplicate/ | JobDuplicateView | 求人複製 |
| /interviews/ | InterviewListView | 面接一覧 |
| /schedule/ | ScheduleView | 面接予定 |
| /personas/ | PersonaListView | ペルソナ一覧 |
| /agents/ | AgentCompanyListView | エージェント一覧 |
| /agent/ | AgentPortalView | エージェントポータル |
| /reports/ | ReportsView | レポート |
| /settings/ | SettingsView | 設定 |
| /users/ | UserManagementView | ユーザー管理 |
| /tenants/ | TenantListView | テナント管理 |

---

## 4. 設計負債対策

### 4.1 マルチテナント設計

**問題**: 後からマルチテナント化は大規模リファクタリング必要

**対策**:
```python
# Phase 1から全テーブルにtenant_id追加
class TenantBaseModel(BaseModel):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        db_index=True  # パフォーマンス対策
    )

    class Meta:
        abstract = True

# TenantMiddlewareで自動フィルタ
class TenantMiddleware:
    def __call__(self, request):
        if request.user.is_authenticated:
            request.tenant = request.user.tenant
        return self.get_response(request)
```

### 4.2 ドメインモデル用語統一

**問題**: 「応募者」「求職者」「候補者」の用語混在

**対策**:
| 日本語 | 英語 | 説明 |
|--------|------|------|
| 候補者 | Candidate | 個人情報を持つ人物 |
| 応募 | Application | 候補者×求人の紐付け |
| 求人 | Job | 募集中のポジション |
| ペルソナ | Persona | 理想候補者像 |

### 4.3 Data Access Layer (DAL) 導入

**問題**: Supabaseへの直接依存でバックエンド変更困難

**対策**:
```python
# apps/core/repositories.py
from abc import ABC, abstractmethod

class CandidateRepository(ABC):
    @abstractmethod
    def get_by_id(self, id: UUID) -> Candidate:
        pass

    @abstractmethod
    def list_by_tenant(self, tenant_id: UUID) -> list[Candidate]:
        pass

class DjangoCandidateRepository(CandidateRepository):
    def get_by_id(self, id: UUID) -> Candidate:
        return Candidate.objects.get(id=id)

    def list_by_tenant(self, tenant_id: UUID) -> list[Candidate]:
        return list(Candidate.objects.filter(tenant_id=tenant_id))
```

### 4.4 ペルソナ管理の設計

**問題**: ペルソナのライフサイクル管理が不明確

**対策**:
- ペルソナCRUD機能をPhase 5.3で実装
- Job-Persona: N:M関係 (JobPersona中間テーブル)
- ペルソナテンプレート機能 (is_template フラグ)

---

## 5. 技術負債対策

### 5.1 環境変数管理

**問題**: ハードコードされた設定値

**対策**:
```python
# config/settings/base.py
import environ

env = environ.Env()
environ.Env.read_env('.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
DATABASE_URL = env('DATABASE_URL')
DEFAULT_TENANT_ID = env('DEFAULT_TENANT_ID', default=None)
```

```bash
# .env.example
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost:5432/django_ats
DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001
SENTRY_DSN=https://xxx@sentry.io/xxx
REDIS_URL=redis://localhost:6379/0
```

### 5.2 テスト戦略拡充

**問題**: テストカバレッジ不足

**対策**:
```python
# tests/conftest.py
import pytest
from tests.factories import TenantFactory, UserFactory, CandidateFactory

@pytest.fixture
def tenant():
    return TenantFactory()

@pytest.fixture
def admin_user(tenant):
    return UserFactory(tenant=tenant, role='client_admin')

@pytest.fixture
def authenticated_client(client, admin_user):
    client.force_login(admin_user)
    return client
```

| テストカテゴリ | 目標件数 | ツール |
|---------------|----------|--------|
| モデルユニット | 70件 (14モデル×5) | pytest |
| ビューテスト | 200件 (20画面×10) | pytest-django |
| 統合テスト | 30件 | pytest |
| E2Eテスト | 30件 | Playwright |
| セキュリティ | 20件 | pytest + OWASP ZAP |

### 5.3 依存ライブラリ管理

**問題**: バージョン固定不足

**対策**:
```txt
# requirements.txt (完全バージョン固定)
Django==5.0.9
django-allauth==0.61.1
django-guardian==2.4.0
django-htmx==1.17.3
django-crispy-forms==2.1
crispy-tailwind==1.0.3
django-filter==24.1
django-environ==0.11.2
psycopg2-binary==2.9.9
gunicorn==21.2.0
whitenoise==6.6.0
celery==5.3.6
redis==5.0.1
sentry-sdk==1.39.1
pytest==8.0.0
pytest-django==4.8.0
pytest-cov==4.1.0
factory-boy==3.3.0
pip-audit==2.7.0  # 脆弱性チェック
```

```yaml
# .github/workflows/security.yml
name: Security Check
on: [push]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pip-audit
      - run: pip-audit -r requirements.txt
```

### 5.4 N+1クエリ対策

**問題**: 一覧ページでN+1クエリ発生

**対策**:
```python
# apps/candidates/views.py
class CandidateListView(TenantAccessMixin, ListView):
    model = Candidate
    paginate_by = 50

    def get_queryset(self):
        return Candidate.objects.filter(
            tenant=self.request.tenant
        ).select_related(
            'agent_company'
        ).prefetch_related(
            'applications',
            'applications__job'
        ).order_by('-created_at')
```

### 5.5 エラーハンドリング標準化

**問題**: エラー時にユーザーに詳細が露出

**対策**:
```python
# apps/core/error_handlers.py
import logging
from django.shortcuts import render
from sentry_sdk import capture_exception

logger = logging.getLogger(__name__)

def handler400(request, exception):
    return render(request, 'errors/400.html', status=400)

def handler403(request, exception):
    logger.warning(f"403 Forbidden: {request.path} by {request.user}")
    return render(request, 'errors/403.html', status=403)

def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    capture_exception()
    return render(request, 'errors/500.html', status=500)
```

```python
# config/urls.py
handler400 = 'apps.core.error_handlers.handler400'
handler403 = 'apps.core.error_handlers.handler403'
handler404 = 'apps.core.error_handlers.handler404'
handler500 = 'apps.core.error_handlers.handler500'
```

### 5.6 CSVインポート設計

**問題**: バリデーション不足、トランザクション未対応

**対策**:
```python
# apps/candidates/services.py
from django.db import transaction
from celery import shared_task
import pandas as pd

class CSVImportService:
    REQUIRED_COLUMNS = ['name', 'email', 'phone']
    CHUNK_SIZE = 1000

    def validate_schema(self, df: pd.DataFrame) -> list[str]:
        errors = []
        for col in self.REQUIRED_COLUMNS:
            if col not in df.columns:
                errors.append(f"必須カラム '{col}' がありません")
        return errors

    @transaction.atomic
    def import_candidates(self, file, tenant, user) -> ImportHistory:
        history = ImportHistory.objects.create(
            tenant=tenant,
            file_name=file.name,
            status='processing',
            created_by=user
        )

        try:
            for chunk in pd.read_csv(file, chunksize=self.CHUNK_SIZE):
                errors = self.validate_schema(chunk)
                if errors:
                    raise ValidationError(errors)

                candidates = [
                    Candidate(
                        tenant=tenant,
                        name=row['name'],
                        email=row['email'],
                        phone=row['phone'],
                        registered_by=user
                    )
                    for _, row in chunk.iterrows()
                ]
                Candidate.objects.bulk_create(candidates)

            history.status = 'completed'
            history.save()

        except Exception as e:
            history.status = 'failed'
            history.error_log = str(e)
            history.save()
            raise

        return history
```

### 5.7 認証トークン管理

**問題**: トークンリフレッシュ戦略不明

**対策**: Django標準セッション認証を使用
```python
# config/settings/base.py
SESSION_COOKIE_AGE = 86400  # 24時間
SESSION_SAVE_EVERY_REQUEST = True  # アクティブ時に延長
SESSION_COOKIE_SECURE = True  # HTTPS only (本番)
SESSION_COOKIE_HTTPONLY = True
```

---

## 6. 不測の事態対策

### 6.1 データベース障害

| 項目 | 対策 |
|------|------|
| 監視 | Supabaseステータスページ監視 + UptimeRobot |
| バックアップ | Supabase自動バックアップ (日次) |
| 復旧手順 | DISASTER_RECOVERY.md 作成 |
| 代替手段 | メンテナンスモード表示 |

### 6.2 認証サービス障害

| 項目 | 対策 |
|------|------|
| 検知 | ログインエラー率監視 (Sentry) |
| 告知 | 障害時告知ページ表示 |
| 影響範囲 | 既存セッションは維持 (新規ログインのみ不可) |

### 6.3 同時編集コンフリクト

| 項目 | 対策 |
|------|------|
| 検知 | versionカラムによる楽観的ロック |
| UI | "他のユーザーが編集中です"メッセージ |
| 解決 | 最新データで再表示、ユーザーに再編集を促す |

```python
# apps/core/mixins.py
class OptimisticLockMixin:
    def form_valid(self, form):
        current = self.get_object()
        if form.instance.version != current.version:
            messages.error(self.request, "他のユーザーが編集しました。再読み込みしてください。")
            return redirect(self.get_object().get_absolute_url())
        return super().form_valid(form)
```

### 6.4 大量データ処理時のメモリ不足

| 項目 | 対策 |
|------|------|
| CSVインポート | chunk読み込み (1000件ずつ) |
| エクスポート | StreamingHttpResponse使用 |
| 大量処理 | Celeryでバックグラウンド実行 |

```python
# apps/candidates/views.py
from django.http import StreamingHttpResponse
import csv

class CandidateExportView(View):
    def get(self, request):
        def generate():
            yield ','.join(['name', 'email', 'phone']) + '\n'
            for candidate in Candidate.objects.filter(
                tenant=request.tenant
            ).iterator(chunk_size=1000):
                yield ','.join([
                    candidate.name,
                    candidate.email or '',
                    candidate.phone or ''
                ]) + '\n'

        response = StreamingHttpResponse(generate(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="candidates.csv"'
        return response
```

### 6.5 CSVインポート失敗時のロールバック

| 項目 | 対策 |
|------|------|
| トランザクション | @transaction.atomic 使用 |
| 履歴記録 | ImportHistoryテーブル |
| エラー詳細 | error_logカラムに記録 |
| 通知 | 失敗時にユーザーへメール通知 (オプション) |

### 6.6 セキュリティインシデント発生

| 項目 | 対策 |
|------|------|
| 検知 | Sentryアラート、異常ログイン監視 |
| 対応 | SECURITY_INCIDENT_RESPONSE.md 作成 |
| 調査 | アクセスログ保存 (90日) |
| 通知 | 影響ユーザーへの通知フロー |

### 6.7 データ漏洩発生時の対応

| 項目 | 対策 |
|------|------|
| アクセスログ | 全API呼び出しをログ記録 |
| 影響範囲特定 | tenant_id + user_id + timestampで追跡 |
| 報告 | 24時間以内に管理者へ報告 |
| 対策 | パスワード強制リセット、セッション無効化 |

### 6.8 Reflexへのロールバック

| 項目 | 対策 |
|------|------|
| コード保持 | reflex_ats/ディレクトリは削除しない |
| DB互換性 | 同一Supabaseを使用、スキーマ互換維持 |
| 切替時間 | 30分以内に切替可能 |
| 判断基準 | P1障害が1時間以内に復旧しない場合 |

### 6.9 本番環境でのバグ発見

| 項目 | 対策 |
|------|------|
| 検知 | Sentryでエラー追跡 |
| 優先度判断 | P1(停止)/P2(重要機能)/P3(軽微) |
| ホットフィックス | mainブランチから直接修正 |
| ロールバック | 直前のタグへ戻す |

### 6.10 依存ライブラリの脆弱性発覚

| 項目 | 対策 |
|------|------|
| 検知 | Dependabot + pip-audit |
| 評価 | CVSS スコアで優先度判断 |
| 対応 | Critical: 24時間以内、High: 72時間以内 |
| テスト | アップデート後の回帰テスト必須 |

---

## 7. 通知機能設計 (要件漏れ対策)

### 7.1 通知種別

| ID | 通知種別 | トリガー | 実装方法 |
|----|----------|----------|----------|
| NTF-001 | アプリ内通知 | 全通知 | Notificationモデル |
| NTF-002 | 新規応募通知 | Application作成時 | Django Signal |
| NTF-003 | ステータス変更通知 | Applicationステータス変更時 | Django Signal |
| NTF-004 | 面接リマインド | 面接日前日 | Celery Beat |
| NTF-005 | 対応期限通知 | 新規応募から3日経過 | Celery Beat |

### 7.2 実装

```python
# apps/notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.applications.models import Application
from apps.notifications.models import Notification

@receiver(post_save, sender=Application)
def create_application_notification(sender, instance, created, **kwargs):
    if created:
        # 新規応募通知
        Notification.objects.create(
            tenant=instance.tenant,
            user=instance.job.created_by,
            type='new_application',
            title=f'新規応募: {instance.candidate.name}',
            message=f'{instance.candidate.name}さんが{instance.job.title}に応募しました',
            link=f'/applications/{instance.id}/'
        )
```

```python
# apps/notifications/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def send_interview_reminders():
    """面接リマインド (毎日9:00に実行)"""
    tomorrow = timezone.now().date() + timedelta(days=1)
    interviews = Interview.objects.filter(
        scheduled_at__date=tomorrow,
        status='scheduled'
    ).select_related('application__candidate', 'interviewer')

    for interview in interviews:
        Notification.objects.create(
            tenant=interview.tenant,
            user=interview.interviewer,
            type='interview_reminder',
            title='明日の面接リマインド',
            message=f'{interview.application.candidate.name}さんとの面接が明日あります',
            link=f'/interviews/{interview.id}/'
        )

@shared_task
def check_pending_applications():
    """対応期限通知 (毎日10:00に実行)"""
    threshold = timezone.now() - timedelta(days=3)
    pending = Application.objects.filter(
        status='新規応募',
        created_at__lt=threshold
    ).select_related('candidate', 'job')

    for app in pending:
        Notification.objects.create(
            tenant=app.tenant,
            user=app.job.created_by,
            type='pending_deadline',
            title='対応期限超過',
            message=f'{app.candidate.name}さんの応募が3日以上未対応です',
            link=f'/applications/{app.id}/'
        )
```

---

## 8. 移行フェーズ

### Phase 1: プロジェクト基盤構築

**目標**: Djangoプロジェクトの骨格を作成

#### タスク
1. [ ] Djangoプロジェクト作成
2. [ ] requirements.txt作成 (バージョン完全固定)
3. [ ] 設定ファイル分割 (base/dev/prod)
4. [ ] 環境変数設定 (.env.example作成)
5. [ ] Tailwind CSS設定
6. [ ] htmx設定
7. [ ] ベーステンプレート作成
8. [ ] エラーページ作成 (400/403/404/500)
9. [ ] Sentry設定

#### 成果物
- manage.py
- config/settings/*.py
- templates/base.html
- templates/errors/*.html
- .env.example

#### テスト
- [ ] `python manage.py check` 成功
- [ ] `python manage.py runserver` 起動確認
- [ ] Tailwind CSSの適用確認

---

### Phase 2: データベースモデル実装

**目標**: 全14テーブル + 追加テーブルのモデル定義

#### タスク
1. [ ] BaseModel, TenantBaseModel作成 (version追加)
2. [ ] Tenantモデル
3. [ ] CustomUser, Profileモデル
4. [ ] AgentCompanyモデル
5. [ ] Candidateモデル
6. [ ] Applicationモデル
7. [ ] ApplicationStatusHistoryモデル
8. [ ] Jobモデル
9. [ ] JobPersona, JobAgentCompanyモデル
10. [ ] Personaモデル
11. [ ] Interviewモデル
12. [ ] StatusSetting, ApplicationSourceモデル
13. [ ] Notificationモデル
14. [ ] ImportHistoryモデル (CSVインポート履歴)
15. [ ] マイグレーション作成・適用

#### テスト
- [ ] 各モデルのユニットテスト (70件)
- [ ] 楽観的ロックのテスト
- [ ] テナント分離のテスト

#### 逆証明
- [ ] 必須フィールドがNULLでエラー
- [ ] 外部キー制約違反でエラー
- [ ] version不一致で更新失敗

---

### Phase 3: 認証・権限システム実装

**目標**: django-allauthによる認証とロール権限

#### タスク
1. [ ] django-allauth設定
2. [ ] CustomUserモデル設定
3. [ ] ログインビュー
4. [ ] サインアップビュー
5. [ ] パスワードリセットビュー
6. [ ] ロール権限Mixin作成
7. [ ] TenantMiddleware作成
8. [ ] OptimisticLockMixin作成

#### テスト
- [ ] ログイン成功・失敗テスト
- [ ] ロール別アクセス制御テスト (4ロール×10操作)
- [ ] テナント分離テスト

#### 逆証明
- [ ] 無効な認証情報でログイン失敗
- [ ] 権限なしで403エラー
- [ ] 他テナントデータにアクセス不可

---

### Phase 4: コア機能移行

**目標**: 候補者・求人・応募管理の移行

#### Phase 4.1: 候補者管理

**タスク**
1. [ ] CandidateListView (一覧)
2. [ ] CandidateDetailView (詳細)
3. [ ] CandidateCreateView (登録)
4. [ ] CandidateUpdateView (編集)
5. [ ] CandidateDeleteView (削除)
6. [ ] フィルタ・検索機能
7. [ ] CSVインポート (トランザクション対応)
8. [ ] CSVエクスポート (ストリーミング対応)
9. [ ] ImportHistory記録

#### Phase 4.2: 求人管理

**タスク**
1. [ ] JobListView
2. [ ] JobDetailView
3. [ ] JobCreateView
4. [ ] JobUpdateView
5. [ ] 求人複製機能
6. [ ] 募集開始/停止機能

#### Phase 4.3: 応募管理

**タスク**
1. [ ] ApplicationListView
2. [ ] ApplicationDetailView
3. [ ] ステータス変更機能
4. [ ] ステータス履歴記録
5. [ ] 楽観的ロック適用

---

### Phase 5: 追加機能移行

#### Phase 5.1: ダッシュボード
1. [ ] 統計サマリー表示
2. [ ] 応募数推移グラフ
3. [ ] 採用ファネル
4. [ ] 未対応応募者一覧

#### Phase 5.2: 面接管理
1. [ ] 面接CRUD
2. [ ] カレンダー表示
3. [ ] 面接記録

#### Phase 5.3: ペルソナ管理
1. [ ] ペルソナCRUD
2. [ ] 求人紐付け
3. [ ] テンプレート機能

#### Phase 5.4: エージェント管理
1. [ ] エージェント会社CRUD
2. [ ] エージェントポータル
3. [ ] 求人依頼機能

#### Phase 5.5: 通知機能
1. [ ] 通知一覧
2. [ ] 既読管理
3. [ ] 新規応募通知 (Signal)
4. [ ] ステータス変更通知 (Signal)
5. [ ] 面接リマインド (Celery)
6. [ ] 対応期限通知 (Celery)

#### Phase 5.6: 設定・レポート
1. [ ] ステータス設定
2. [ ] 応募経路設定
3. [ ] 応募数レポート
4. [ ] ファネル分析
5. [ ] エージェント実績

---

### Phase 6: 統合テスト・E2Eテスト

#### タスク
1. [ ] 統合テスト作成 (30件)
2. [ ] E2Eテスト (Playwright) (30件)
3. [ ] セキュリティテスト (20件)
4. [ ] パフォーマンステスト
5. [ ] OWASP ZAPスキャン

#### セキュリティ逆証明テスト

| テスト項目 | 逆証明 |
|------------|--------|
| 認証必須 | 未ログインでアクセス不可 |
| テナント分離 | 他テナントデータ取得不可 |
| 権限チェック | 権限なしで操作不可 |
| CSRF | CSRFトークンなしでPOST不可 |
| XSS | スクリプト注入が無効化 |
| SQLインジェクション | Django ORMで防御 |

---

### Phase 7: デプロイ準備

#### タスク
1. [ ] production.py設定
2. [ ] セキュリティ設定確認
3. [ ] 環境変数設定
4. [ ] 静的ファイル収集
5. [ ] Gunicorn設定
6. [ ] Celery設定
7. [ ] デプロイスクリプト作成
8. [ ] 監視設定 (UptimeRobot)
9. [ ] ドキュメント整備

#### セキュリティ設定チェックリスト
- [ ] DEBUG = False
- [ ] SECRET_KEY 環境変数化
- [ ] ALLOWED_HOSTS 設定
- [ ] SECURE_SSL_REDIRECT = True
- [ ] SESSION_COOKIE_SECURE = True
- [ ] CSRF_COOKIE_SECURE = True
- [ ] SECURE_HSTS_SECONDS = 31536000
- [ ] X_FRAME_OPTIONS = 'DENY'

---

## 9. ドキュメント一覧

| ドキュメント | 目的 | 作成Phase |
|--------------|------|-----------|
| MIGRATION_PLAN.md | 移行計画 | Phase 0 |
| REQUIREMENTS_SUMMARY.md | 要件サマリー | Phase 0 |
| DEBT_ANALYSIS.md | 負債分析 | Phase 0 |
| DISASTER_RECOVERY.md | 障害復旧手順 | Phase 7 |
| SECURITY_INCIDENT_RESPONSE.md | インシデント対応 | Phase 7 |
| DEPLOYMENT_GUIDE.md | デプロイ手順 | Phase 7 |
| OPERATION_MANUAL.md | 運用マニュアル | Phase 7 |

---

## 10. 承認

| 役割 | 氏名 | 日付 | 署名 |
|------|------|------|------|
| 計画作成者 | Claude | 2025/12/24 | - |
| レビュー者 | Claude (system-architect) | 2025/12/24 | - |
| 承認者 | | | |

---

## 付録A: 依存パッケージ一覧

```
# requirements.txt
Django==5.0.9
django-allauth==0.61.1
django-guardian==2.4.0
django-htmx==1.17.3
django-crispy-forms==2.1
crispy-tailwind==1.0.3
django-filter==24.1
django-environ==0.11.2
psycopg2-binary==2.9.9
gunicorn==21.2.0
whitenoise==6.6.0
celery==5.3.6
redis==5.0.1
sentry-sdk==1.39.1
pytest==8.0.0
pytest-django==4.8.0
pytest-cov==4.1.0
factory-boy==3.3.0
pip-audit==2.7.0
pandas==2.1.4
```

## 付録B: 環境変数一覧

```
# .env.example
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost:5432/django_ats
ALLOWED_HOSTS=localhost,127.0.0.1
DEFAULT_TENANT_ID=00000000-0000-0000-0000-000000000001

# Celery
REDIS_URL=redis://localhost:6379/0

# Sentry
SENTRY_DSN=https://xxx@sentry.io/xxx

# Supabase (オプション、移行期間中のみ)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
```
