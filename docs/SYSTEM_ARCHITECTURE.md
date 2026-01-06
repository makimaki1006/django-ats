# Django ATS - システムアーキテクチャ

**バージョン**: 1.0
**最終更新**: 2026年1月

---

## 1. システム概要

Django ATS は、採用コンサルティング会社向けのマルチテナント採用管理システム（ATS: Applicant Tracking System）です。

### 1.1 主要な特徴

- **マルチテナント**: 複数の顧客企業（テナント）を1つのシステムで管理
- **スプレッドシート連携**: Google Spreadsheet との双方向同期
- **ロールベースアクセス制御**: 7種類のユーザーロールによる細かな権限管理
- **2スプレッドシート構成**: 業務用（顧客閲覧可）と管理用（コンサルタント専用）

### 1.2 技術スタック

```
┌─────────────────────────────────────────────────────────────┐
│                        フロントエンド                         │
│  Django Templates + HTMX + Tailwind CSS                     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        バックエンド                           │
│  Django 5.x + Python 3.12                                   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌─────────────────────┐                 ┌─────────────────────┐
│    PostgreSQL       │                 │  Google Spreadsheet │
│   (認証・テナント)   │                 │   (業務データ)       │
└─────────────────────┘                 └─────────────────────┘
```

---

## 2. アーキテクチャ構成図

### 2.1 全体構成

```
                                ┌─────────────────────────────────┐
                                │         ユーザーアクセス          │
                                │  ブラウザ (HTMX + Tailwind)      │
                                └────────────────┬────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              Django Application                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           Presentation Layer                          │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │  │
│  │  │ Views   │ │Templates│ │ Forms   │ │ Mixins  │ │  URLs   │        │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           Business Logic Layer                        │  │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐        │  │
│  │  │    Services     │ │   Validators    │ │   Permissions   │        │  │
│  │  │                 │ │                 │ │                 │        │  │
│  │  │ Spreadsheet     │ │  Role-based     │ │  Tenant-based   │        │  │
│  │  │ SyncService     │ │  Access Control │ │  Isolation      │        │  │
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                              Data Layer                               │  │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐        │  │
│  │  │     Models      │ │    Managers     │ │   QuerySets     │        │  │
│  │  │  - BaseModel    │ │  - Custom       │ │  - for_user()   │        │  │
│  │  │  - TenantBase   │ │    filtering    │ │  - active()     │        │  │
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
           │                                              │
           ▼                                              ▼
┌─────────────────────────┐                 ┌─────────────────────────┐
│      PostgreSQL         │                 │    Google Spreadsheet   │
│  ┌───────────────────┐  │                 │  ┌───────────────────┐  │
│  │ accounts.User     │  │                 │  │   業務用シート     │  │
│  │ tenants.Tenant    │  │                 │  │  - 候補者          │  │
│  │ tenants.Spread... │  │                 │  │  - 求人            │  │
│  │ settings_app.*    │  │                 │  │  - 応募            │  │
│  │ core.AuditLog     │  │                 │  │  - 面接            │  │
│  └───────────────────┘  │                 │  └───────────────────┘  │
│                         │                 │  ┌───────────────────┐  │
│                         │                 │  │   管理用シート     │  │
│                         │                 │  │  - ユーザー        │  │
│                         │                 │  │  (パスワード含む)  │  │
│                         │                 │  └───────────────────┘  │
└─────────────────────────┘                 └─────────────────────────┘
```

---

## 3. データベース設計

### 3.1 ER図（エンティティ関連図）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE MODELS                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Tenant     │────1:N──│  CustomUser  │────1:1──│   Profile    │
│──────────────│         │──────────────│         │──────────────│
│ id (UUID)    │         │ id (UUID)    │         │ id (UUID)    │
│ name         │         │ email        │         │ user_id      │
│ code         │         │ tenant_id    │         │ display_name │
│ plan         │         │ role         │         │ phone        │
│ max_users    │         │ is_active    │         │ agent_co_id  │
│ is_active    │         │ created_at   │         │ notification │
│ settings     │         │ updated_at   │         │ settings     │
└──────┬───────┘         └──────────────┘         └──────────────┘
       │
       │ 1:1
       ▼
┌──────────────────┐
│ TenantSpreadsheet│
│──────────────────│
│ tenant_id        │
│ spreadsheet_id   │        (業務用)
│ admin_spread_id  │        (管理用)
│ is_active        │
│ last_synced_at   │
└──────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                             BUSINESS MODELS                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Candidate   │────N:1──│   Tenant     │──1:N────│     Job      │
│──────────────│         └──────────────┘         │──────────────│
│ id (UUID)    │                                  │ id (UUID)    │
│ tenant_id    │                                  │ tenant_id    │
│ name         │                                  │ title        │
│ email        │                                  │ unique_code  │
│ phone        │                                  │ status       │
│ gender       │                                  │ department   │
│ birth_date   │                                  │ salary_min   │
│ current_co   │                                  │ salary_max   │
│ skills       │◄─────────────────┐               │ description  │
│ agent_co_id  │                  │               └───────┬──────┘
│ is_archived  │                  │                       │
└──────┬───────┘                  │                       │
       │                          │                       │
       │ 1:N                      │                       │ N:M
       ▼                          │                       ▼
┌──────────────┐                  │              ┌──────────────┐
│ Application  │──────────────────┘              │   Persona    │
│──────────────│                                 │──────────────│
│ id (UUID)    │                                 │ id (UUID)    │
│ candidate_id │                                 │ tenant_id    │
│ job_id       │                                 │ name         │
│ status       │                                 │ age_min/max  │
│ applied_at   │                                 │ exp_years    │
│ eval_score   │                                 │ skills       │
│ offer_salary │                                 │ education    │
└──────┬───────┘                                 │ is_template  │
       │                                         └──────────────┘
       │ 1:N
       ▼
┌──────────────┐
│  Interview   │
│──────────────│
│ id (UUID)    │
│ app_id       │
│ type         │
│ round        │
│ scheduled_at │
│ interviewer  │
│ status       │
│ result       │
│ eval_score   │
└──────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                             MASTER DATA                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│ AgentCompany │         │ ApplicationSource│         │ EmailTemplate│
│──────────────│         │──────────────────│         │──────────────│
│ id (UUID)    │         │ id (UUID)        │         │ id (UUID)    │
│ name         │         │ tenant_id (opt)  │         │ tenant_id    │
│ code         │         │ name             │         │ name         │
│ tenant_id    │         │ source_type      │         │ template_type│
│ fee_rate     │         │ is_active        │         │ subject      │
│ is_active    │         └──────────────────┘         │ body         │
│ is_preferred │                                      │ is_default   │
└──────────────┘                                      └──────────────┘
```

### 3.2 モデル継承構造

```
                    ┌─────────────────┐
                    │   models.Model  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
      ┌───────────┐  ┌─────────────┐  ┌──────────────┐
      │ BaseModel │  │ AuditLog    │  │ LoginHistory │
      │───────────│  │ (独立)      │  │ (独立)       │
      │ id (UUID) │  └─────────────┘  └──────────────┘
      │ created_at│
      │ updated_at│
      │ version   │
      └─────┬─────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
┌───────────────┐ ┌─────────────────┐
│TenantBaseModel│ │ SoftDeleteModel │
│───────────────│ │─────────────────│
│ tenant (FK)   │ │ is_deleted      │
└───────┬───────┘ │ deleted_at      │
        │         └─────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│ Candidate, Job, Application, Interview,         │
│ Persona, StatusSetting, EmailTemplate, Profile  │
└─────────────────────────────────────────────────┘
```

---

## 4. アプリケーション構成

### 4.1 Djangoアプリ一覧

```
django_ats/
├── config/                    # プロジェクト設定
│   ├── settings/
│   │   ├── base.py           # 共通設定
│   │   ├── development.py    # 開発環境
│   │   └── production.py     # 本番環境
│   ├── urls.py               # ルートURL設定
│   └── wsgi.py               # WSGIエントリポイント
│
├── apps/
│   ├── core/                  # 共通機能
│   │   ├── models.py         # BaseModel, TenantBaseModel, AuditLog
│   │   ├── mixins.py         # HtmxMixin, PaginationMixin, SearchMixin
│   │   └── services/         # ビジネスロジック
│   │       └── spreadsheet_sync.py  # スプレッドシート同期
│   │
│   ├── accounts/              # ユーザー管理
│   │   ├── models.py         # CustomUser, Profile, LoginHistory
│   │   ├── views.py          # 認証・ユーザー管理ビュー
│   │   └── forms.py          # ユーザーフォーム
│   │
│   ├── tenants/               # テナント管理
│   │   ├── models.py         # Tenant, TenantSpreadsheet
│   │   ├── views.py          # テナント管理ビュー
│   │   └── services.py       # テナント関連サービス
│   │
│   ├── candidates/            # 候補者管理
│   │   ├── models.py         # Candidate, CandidateComment
│   │   ├── views.py          # 候補者CRUD
│   │   └── services.py       # 候補者サービス
│   │
│   ├── jobs/                  # 求人管理
│   │   ├── models.py         # Job, JobPersona, JobAgentCompany
│   │   ├── views.py          # 求人CRUD
│   │   └── forms.py          # 求人フォーム
│   │
│   ├── applications/          # 応募管理
│   │   ├── models.py         # Application, ApplicationStatusHistory
│   │   ├── views.py          # 応募管理ビュー
│   │   └── forms.py          # 応募フォーム
│   │
│   ├── interviews/            # 面接管理
│   │   ├── models.py         # Interview, InterviewFeedbackRequest
│   │   ├── views.py          # 面接管理ビュー
│   │   └── forms.py          # 面接フォーム
│   │
│   ├── personas/              # ペルソナ管理
│   │   ├── models.py         # Persona
│   │   ├── views.py          # ペルソナCRUD
│   │   └── forms.py          # ペルソナフォーム
│   │
│   ├── agents/                # エージェント会社管理
│   │   ├── models.py         # AgentCompany
│   │   ├── views.py          # エージェント管理ビュー
│   │   └── forms.py          # エージェントフォーム
│   │
│   ├── settings_app/          # 設定管理
│   │   ├── models.py         # StatusSetting, ApplicationSource, EmailTemplate
│   │   ├── views.py          # 設定管理ビュー
│   │   └── forms.py          # 設定フォーム
│   │
│   ├── notifications/         # 通知管理
│   │   └── models.py         # Notification
│   │
│   └── reports/               # レポート
│       └── models.py         # Report
│
├── templates/                 # HTMLテンプレート
│   ├── base.html             # ベーステンプレート
│   ├── accounts/
│   ├── tenants/
│   ├── candidates/
│   ├── jobs/
│   ├── applications/
│   ├── interviews/
│   └── ...
│
└── static/                    # 静的ファイル
    ├── css/
    └── js/
```

---

## 5. ユーザーロールと権限

### 5.1 ロール定義

| ロール | 日本語名 | アクセス範囲 | 主な機能 |
|--------|----------|-------------|----------|
| `system_admin` | システム管理者 | 全テナント | システム全体の管理 |
| `consultant` | 採用コンサルタント | 担当テナント | テナント支援、設定、レポート |
| `client_admin` | 人事担当者 | 自テナント | テナント設定、ユーザー招待 |
| `hiring_manager` | 採用責任者 | 自テナント | 全候補者アクセス、承認 |
| `client_recruiter` | 企業担当者 | 自テナント | 応募者・求人・面接管理 |
| `interviewer` | 面接官 | 担当面接のみ | 担当面接の候補者閲覧・評価 |
| `agent` | 人材紹介会社 | 自社紹介のみ | 自社紹介候補者の閲覧・登録 |

### 5.2 権限マトリクス

```
                    │ sys_admin │ consultant │ client_admin │ hiring_mgr │ recruiter │ interviewer │ agent │
────────────────────┼───────────┼────────────┼──────────────┼────────────┼───────────┼─────────────┼───────┤
テナント管理        │     ✓     │     ✓      │      ✓       │     -      │     -     │      -      │   -   │
ユーザー管理        │     ✓     │     ✓      │      ✓       │     -      │     -     │      -      │   -   │
全候補者閲覧        │     ✓     │     ✓      │      ✓       │     ✓      │     ✓     │      -      │   -   │
担当候補者閲覧      │     ✓     │     ✓      │      ✓       │     ✓      │     ✓     │      ✓      │   ✓   │
求人管理            │     ✓     │     ✓      │      ✓       │     ✓      │     ✓     │      -      │   -   │
応募管理            │     ✓     │     ✓      │      ✓       │     ✓      │     ✓     │      -      │   -   │
面接管理            │     ✓     │     ✓      │      ✓       │     ✓      │     ✓     │      ✓      │   -   │
面接評価入力        │     ✓     │     ✓      │      ✓       │     ✓      │     ✓     │      ✓      │   -   │
レポート閲覧        │     ✓     │     ✓      │      ✓       │     ✓      │     -     │      -      │   -   │
設定変更            │     ✓     │     ✓      │      ✓       │     -      │     -     │      -      │   -   │
スプレッドシート同期│     ✓     │     ✓      │      -       │     -      │     -     │      -      │   -   │
```

---

## 6. データフロー

### 6.1 スプレッドシート同期アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         スプレッドシート同期フロー                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐                              ┌──────────────────┐
│   Django ATS     │                              │ Google Spreadsheet│
│                  │                              │                  │
│  ┌────────────┐  │                              │  ┌────────────┐  │
│  │ PostgreSQL │  │        Push (App→Sheet)      │  │   業務用   │  │
│  │            │  │  ─────────────────────────►  │  │            │  │
│  │ - User     │  │                              │  │ - 候補者   │  │
│  │ - Tenant   │  │        Pull (Sheet→App)      │  │ - 求人     │  │
│  │ - Spread   │  │  ◄─────────────────────────  │  │ - 応募     │  │
│  │   sheet ID │  │                              │  │ - 面接     │  │
│  │            │  │                              │  │            │  │
│  └────────────┘  │                              │  └────────────┘  │
│                  │                              │                  │
│  ┌────────────┐  │        Push (Users)          │  ┌────────────┐  │
│  │Spreadsheet │  │  ─────────────────────────►  │  │   管理用   │  │
│  │SyncService │  │                              │  │            │  │
│  │            │  │        Pull (Users)          │  │ - ユーザー │  │
│  │- sync_all()│  │  ◄─────────────────────────  │  │ - パスワード│  │
│  │- push_*()  │  │                              │  │            │  │
│  │- pull_*()  │  │                              │  │            │  │
│  └────────────┘  │                              │  └────────────┘  │
└──────────────────┘                              └──────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         同期サービスメソッド一覧                             │
├─────────────────┬───────────────────────────────────────────────────────────┤
│ sync_all()      │ 全データの双方向同期（候補者→求人→応募→面接）            │
│ push_candidates()│ 候補者データをスプレッドシートに書き込み                 │
│ pull_candidates()│ スプレッドシートから候補者データを取得                   │
│ push_jobs()     │ 求人データをスプレッドシートに書き込み                    │
│ pull_jobs()     │ スプレッドシートから求人データを取得                      │
│ push_users()    │ ユーザーを管理用シートに書き込み                         │
│ pull_users()    │ 管理用シートからユーザーを取得・作成                     │
│ create_tenant_spreadsheets() │ 雛形スプレッドシートを自動作成             │
└─────────────────┴───────────────────────────────────────────────────────────┘
```

### 6.2 認証・認可フロー

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            認証・認可フロー                                  │
└─────────────────────────────────────────────────────────────────────────────┘

     ユーザー                   Django                    PostgreSQL
        │                         │                           │
        │  1. ログイン要求         │                           │
        │ (email, password) ────►│                           │
        │                         │  2. ユーザー検索           │
        │                         │ ─────────────────────────►│
        │                         │                           │
        │                         │  3. User + Tenant情報     │
        │                         │ ◄─────────────────────────│
        │                         │                           │
        │                         │  4. パスワード検証         │
        │                         │  5. ロール確認             │
        │                         │  6. テナント有効確認       │
        │                         │                           │
        │  7. セッション発行      │                           │
        │ ◄─────────────────────│                           │
        │                         │                           │
        │  8. データ要求          │                           │
        │  /candidates/ ────────►│                           │
        │                         │  9. ロールベースフィルタ   │
        │                         │                           │
        │                         │ ┌───────────────────────┐ │
        │                         │ │ if has_full_access:   │ │
        │                         │ │   return all_tenant   │ │
        │                         │ │ elif is_interviewer:  │ │
        │                         │ │   return my_interviews│ │
        │                         │ │ elif is_agent:        │ │
        │                         │ │   return my_referrals │ │
        │                         │ └───────────────────────┘ │
        │                         │                           │
        │  10. 許可データ返却     │                           │
        │ ◄─────────────────────│                           │
        │                         │                           │

```

---

## 7. URL構成

### 7.1 主要URLパターン

```
/                                    # ダッシュボード
/accounts/
    login/                           # ログイン
    logout/                          # ログアウト
    users/                           # ユーザー一覧
    users/create/                    # ユーザー作成
    users/<uuid>/                    # ユーザー詳細
    users/<uuid>/edit/               # ユーザー編集
    users/sync/                      # スプレッドシート同期

/tenants/                            # [管理者のみ]
    (empty)                          # テナント一覧
    create/                          # テナント作成
    <uuid>/                          # テナント詳細
    <uuid>/edit/                     # テナント編集
    <uuid>/spreadsheet/              # スプレッドシート設定
    <uuid>/spreadsheet/create/       # スプレッドシート雛形作成
    <uuid>/spreadsheet/sync/         # スプレッドシート同期実行

/candidates/
    (empty)                          # 候補者一覧
    create/                          # 候補者作成
    <uuid>/                          # 候補者詳細
    <uuid>/edit/                     # 候補者編集
    <uuid>/comments/                 # コメント一覧

/jobs/
    (empty)                          # 求人一覧
    create/                          # 求人作成
    <uuid>/                          # 求人詳細
    <uuid>/edit/                     # 求人編集
    <uuid>/duplicate/                # 求人複製

/applications/
    (empty)                          # 応募一覧
    create/                          # 応募作成
    <uuid>/                          # 応募詳細
    <uuid>/change-status/            # ステータス変更

/interviews/
    (empty)                          # 面接一覧
    create/                          # 面接作成
    <uuid>/                          # 面接詳細
    <uuid>/complete/                 # 面接完了・評価入力
    support/                         # 面接サポートページ

/personas/
    (empty)                          # ペルソナ一覧
    create/                          # ペルソナ作成
    <uuid>/                          # ペルソナ詳細

/agents/
    (empty)                          # エージェント一覧
    create/                          # エージェント作成
    <uuid>/                          # エージェント詳細

/settings/
    (empty)                          # 設定ダッシュボード
    status/                          # ステータス設定
    sources/                         # 応募経路設定
    templates/                       # メールテンプレート

/reports/
    (empty)                          # レポートダッシュボード
    pipeline/                        # 採用パイプライン
    performance/                     # パフォーマンスレポート
```

---

## 8. デプロイアーキテクチャ

### 8.1 本番環境構成（Render）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Render Platform                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────┐
                    │          CloudFlare CDN          │
                    │   (Static Assets + SSL/TLS)      │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │         Render Web Service       │
                    │  ┌──────────────────────────┐   │
                    │  │     Gunicorn + Django     │   │
                    │  │                          │   │
                    │  │  - WhiteNoise (静的)     │   │
                    │  │  - Health Check (/health)│   │
                    │  └──────────────────────────┘   │
                    │              │                   │
                    └──────────────┼───────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
    ┌──────────────────┐  ┌──────────────┐   ┌──────────────────┐
    │ Render PostgreSQL │  │ Google Cloud │   │   Render Redis   │
    │                  │  │ (Sheets API) │   │   (Session/Cache)│
    │  - User data     │  │              │   │                  │
    │  - Tenant data   │  │ Spreadsheets │   │                  │
    │  - Config data   │  │              │   │                  │
    └──────────────────┘  └──────────────┘   └──────────────────┘
```

### 8.2 環境変数設定

```
# Django
DJANGO_SECRET_KEY=xxx
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_ALLOWED_HOSTS=your-app.onrender.com

# Database
DATABASE_URL=postgres://user:password@host:5432/dbname

# Redis (Optional)
REDIS_URL=redis://host:6379

# Google API
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Security
CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com
```

---

## 9. セキュリティ設計

### 9.1 セキュリティ対策一覧

| 脅威 | 対策 | 実装場所 |
|------|------|----------|
| SQLインジェクション | Django ORM使用 | 全モデル |
| XSS | テンプレート自動エスケープ | テンプレート |
| CSRF | CSRFトークン検証 | フォーム |
| セッションハイジャック | セキュアCookie設定 | settings.py |
| 権限昇格 | ロールベースアクセス制御 | ビュー |
| テナント間データ漏洩 | テナントフィルタリング | QuerySet |
| ブルートフォース | ログイン試行制限 | LoginHistory |
| パスワード漏洩 | bcryptハッシュ化 | CustomUser |

### 9.2 監査ログ

```python
# apps/core/models.py - AuditLog

class AuditLog:
    timestamp     # 操作日時
    user          # 操作ユーザー
    tenant        # テナント
    action        # 操作種類 (create/update/delete/login/...)
    resource_type # リソース種別
    resource_id   # リソースID
    ip_address    # クライアントIP
    user_agent    # ユーザーエージェント
    changes       # 変更内容 (JSON)
```

---

## 10. 今後の拡張予定

### 10.1 短期（〜3ヶ月）

- [ ] メール送信機能（面接案内、内定通知）
- [ ] CSVインポート/エクスポート機能強化
- [ ] レポートダッシュボード

### 10.2 中期（3〜6ヶ月）

- [ ] API（REST/GraphQL）公開
- [ ] Webhook連携
- [ ] カレンダー連携（Google Calendar）

### 10.3 長期（6ヶ月〜）

- [ ] AIアシスタント（履歴書解析、マッチング）
- [ ] モバイルアプリ対応
- [ ] 多言語対応

---

## 付録A: 用語集

| 用語 | 説明 |
|------|------|
| ATS | Applicant Tracking System（応募者追跡システム） |
| テナント | 顧客企業。データは完全に分離される |
| ペルソナ | 理想的な候補者像の定義 |
| エージェント | 人材紹介会社 |
| 業務用シート | 候補者・求人・応募・面接データ（顧客閲覧可） |
| 管理用シート | ユーザー・パスワードデータ（コンサルタント専用） |

---

## 付録B: 参考リンク

- [Django公式ドキュメント](https://docs.djangoproject.com/)
- [HTMX公式ドキュメント](https://htmx.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [gspread (Google Sheets API)](https://docs.gspread.org/)
- [Render デプロイガイド](https://render.com/docs)
