# Django ATS 要件サマリー

## 移行元: PRD v1.1 (2025/11/27)

---

## 1. ユーザーロール (4種類)

| ロール | 説明 | 権限 |
|--------|------|------|
| system_admin | medica社内管理者 | 全テナント横断 |
| client_admin | 企業人事管理者 | 自テナント全権限 |
| client_recruiter | 企業人事一般 | 閲覧・編集のみ |
| agent | エージェント担当者 | 自社候補者のみ |

---

## 2. データベーステーブル (14テーブル)

### コアテーブル
1. tenants - テナント
2. profiles - ユーザー
3. candidates - 候補者
4. applications - 応募
5. jobs - 求人票
6. personas - ペルソナ
7. interviews - 面接

### エージェント関連
8. agent_companies - エージェント会社
9. job_agent_companies - 求人-エージェント紐付け

### 履歴・設定
10. application_status_history - ステータス履歴
11. job_personas - 求人-ペルソナ紐付け
12. status_settings - ステータス定義
13. application_sources - 応募経路
14. notifications - 通知

---

## 3. 画面一覧 (20画面)

### 認証
- / : ログイン
- /signup : 新規登録
- /reset-password : パスワードリセット

### メイン機能
- /dashboard : ダッシュボード
- /applicants : 応募者一覧
- /candidates/[id] : 候補者詳細
- /applications : 応募管理
- /pending : 未対応応募者
- /jobs : 求人票一覧
- /interviews : 面接管理
- /schedule : 面接予定
- /personas : ペルソナ管理
- /reports : レポート
- /settings : 設定

### 管理機能
- /users : ユーザー管理
- /tenants : テナント管理
- /agent-companies : エージェント会社管理
- /agent : エージェントポータル

---

## 4. 主要機能

### 認証・ユーザー管理
- AUTH-001: ログイン
- AUTH-002: ログアウト
- AUTH-003: パスワードリセット
- USER-001-004: ユーザーCRUD

### 応募者管理
- APP-001-008: 応募者CRUD、ステータス変更、CSV入出力

### 求人票管理
- JOB-001-006: 求人CRUD、募集開始/停止

### 面接管理
- INT-001-005: 面接登録、カレンダー、リマインダー

### 通知機能
- NTF-001-005: アプリ内通知

### ダッシュボード・レポート
- DSH-001-005: 統計、ファネル分析

---

## 5. Django技術スタック

| 項目 | 技術 |
|------|------|
| フレームワーク | Django 5.x |
| 認証 | django-allauth |
| 権限管理 | django-guardian |
| UI | htmx + Tailwind CSS |
| フォーム | django-crispy-forms |
| フィルタ | django-filter |
| REST API | Django REST Framework (オプション) |
| テスト | pytest-django |
| データベース | PostgreSQL (Supabase継続可能) |

---

## 6. ディレクトリ構成 (計画)

```
django_ats/
├── manage.py
├── requirements.txt
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/      # 認証・ユーザー管理
│   ├── tenants/       # テナント管理
│   ├── candidates/    # 候補者管理
│   ├── applications/  # 応募管理
│   ├── jobs/          # 求人管理
│   ├── interviews/    # 面接管理
│   ├── personas/      # ペルソナ管理
│   ├── agents/        # エージェント管理
│   ├── notifications/ # 通知
│   ├── reports/       # レポート
│   └── core/          # 共通機能
├── templates/
│   ├── base.html
│   ├── components/
│   └── pages/
├── static/
│   ├── css/
│   └── js/
└── tests/
```

---

## 7. 移行計画

### Phase 1: 基盤構築 (1日)
- Djangoプロジェクト作成
- 設定ファイル構成
- Tailwind CSS設定

### Phase 2: モデル実装 (1日)
- 全14テーブルのモデル定義
- マイグレーション作成・適用
- ユニットテスト

### Phase 3: 認証実装 (1日)
- django-allauth設定
- カスタムユーザーモデル
- ロール・権限管理

### Phase 4: コア機能 (2-3日)
- 候補者CRUD
- 求人CRUD
- 応募管理

### Phase 5: 追加機能 (2日)
- ダッシュボード
- レポート
- 通知

### Phase 6: テスト・デプロイ (1日)
- E2Eテスト
- デプロイ設定
