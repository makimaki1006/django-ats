# Django ATS - 採用管理システム

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)
[![Test Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](https://github.com/makimaki1006/django-ats)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

マルチテナント対応の採用管理システム（ATS: Applicant Tracking System）です。採用コンサルティング会社が顧客企業に提供するSaaS型ATSとして設計されています。

## 主な機能

### 候補者管理
- 候補者情報の一元管理
- 応募経路トラッキング
- スキル・資格・職歴管理
- コメント・タイムライン機能

### 求人管理
- 求人票の作成・公開管理
- ペルソナ連携
- エージェント会社連携

### 選考プロセス
- 応募ステータス管理
- カンバンボード表示
- 面接スケジュール管理
- 面接評価入力

### マルチテナント
- テナント分離によるデータセキュリティ
- ロールベースアクセス制御
- エージェント会社向け限定アクセス

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| バックエンド | Django 5.0, Python 3.11+ |
| フロントエンド | htmx, Tailwind CSS, Alpine.js |
| データベース | PostgreSQL (本番), SQLite (開発) |
| 認証 | django-allauth |
| タスクキュー | Celery + Redis |
| テスト | pytest, pytest-django, pytest-cov |

## ユーザー種別

| ユーザー種別 | 説明 |
|-------------|------|
| 採用コンサルタント | ATSを提供・運営。顧客企業の採用を支援 |
| 人事担当者 | 顧客企業の採用担当。日常的にATSを操作 |
| 採用責任者 | 顧客企業の採用決定者 |
| 面接官 | 顧客企業の面接実施者（担当面接のみアクセス可） |
| 人材紹介会社 | 外部パートナー（自社紹介の候補者のみアクセス可） |

## セットアップ

### 必要条件

- Python 3.11+
- PostgreSQL 14+ (本番環境)
- Redis (Celeryを使用する場合)

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/makimaki1006/django-ats.git
cd django-ats

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .envを編集してDATABASE_URL等を設定

# データベースマイグレーション
python manage.py migrate

# スーパーユーザー作成
python manage.py createsuperuser

# 開発サーバー起動
python manage.py runserver
```

### 環境変数

```bash
# .env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:pass@localhost:5432/django_ats
ALLOWED_HOSTS=localhost,127.0.0.1

# Google Sheets連携（オプション）
GOOGLE_CREDENTIALS_PATH=path/to/credentials.json
```

## テスト

```bash
# 全テスト実行
pytest

# カバレッジ付きで実行
pytest --cov=apps --cov-report=html

# 特定のアプリのテスト
pytest tests/test_candidates.py -v
```

### テストカバレッジ

| 項目 | 値 |
|------|-----|
| テスト数 | 1,068 |
| カバレッジ | 99% |
| 未カバー行 | 37 |

## プロジェクト構成

```
django_ats/
├── apps/                    # Djangoアプリケーション
│   ├── accounts/            # ユーザー認証・プロファイル
│   ├── agents/              # エージェント会社管理
│   ├── applications/        # 応募管理
│   ├── candidates/          # 候補者管理
│   ├── core/                # 共通機能・ミックスイン
│   ├── interviews/          # 面接管理
│   ├── jobs/                # 求人管理
│   ├── notifications/       # 通知機能
│   ├── personas/            # ペルソナ管理
│   ├── reports/             # レポート機能
│   ├── settings_app/        # システム設定
│   └── tenants/             # テナント管理
├── config/                  # Django設定
├── docs/                    # ドキュメント
├── templates/               # HTMLテンプレート
├── static/                  # 静的ファイル
├── tests/                   # テストファイル
└── manage.py
```

## ドキュメント

- [要件定義書](docs/01_REQUIREMENTS.md)
- [業務フロー](docs/02_BUSINESS_FLOW.md)
- [画面設計](docs/03_SCREEN_DESIGN.md)
- [Googleスプレッドシート連携ガイド](docs/04_GOOGLE_SHEETS_GUIDE.md)

## 開発

### コーディング規約

- PEP 8準拠
- 型ヒント推奨
- docstringは日本語

### ブランチ戦略

- `master` - 本番リリース用
- `develop` - 開発用
- `feature/*` - 機能開発用

## ライセンス

MIT License

## 作者

- GitHub: [@makimaki1006](https://github.com/makimaki1006)
