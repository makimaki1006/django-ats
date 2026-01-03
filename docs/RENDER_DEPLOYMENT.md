# Render.com デプロイガイド

## 概要

Django ATSをRender.comにデプロイするためのガイドです。

## 前提条件

- GitHubアカウント
- Renderアカウント（https://render.com）
- リポジトリがGitHubにプッシュ済み

## デプロイ方法

### 方法1: Blueprint（推奨）

1. Renderダッシュボードにログイン
2. 「New」→「Blueprint」を選択
3. GitHubリポジトリを接続
4. `render.yaml`が自動検出され、以下が作成されます：
   - PostgreSQLデータベース
   - Webサービス

### 方法2: 手動設定

1. **データベース作成**
   - 「New」→「PostgreSQL」
   - Name: `django-ats-db`
   - Region: Singapore
   - Plan: Starter

2. **Webサービス作成**
   - 「New」→「Web Service」
   - GitHubリポジトリを接続
   - 設定:
     - Name: `django-ats`
     - Region: Singapore
     - Branch: `master`
     - Runtime: Python
     - Build Command: `./build.sh`
     - Start Command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

## 環境変数

### 必須

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `SECRET_KEY` | Djangoシークレットキー | 自動生成推奨 |
| `DATABASE_URL` | PostgreSQL接続文字列 | 自動設定（Blueprint使用時） |
| `DJANGO_SETTINGS_MODULE` | 設定モジュール | `config.settings.production` |
| `ALLOWED_HOSTS` | 許可ホスト | `.onrender.com` |

### オプション

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `DEBUG` | デバッグモード | `False` |
| `CSRF_TRUSTED_ORIGINS` | CSRF信頼オリジン | `https://*.onrender.com` |
| `SENTRY_DSN` | Sentry DSN | （空） |
| `EMAIL_HOST` | SMTPホスト | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTPポート | `587` |
| `EMAIL_HOST_USER` | SMTPユーザー | （空） |
| `EMAIL_HOST_PASSWORD` | SMTPパスワード | （空） |
| `DEFAULT_FROM_EMAIL` | 送信元メール | `noreply@example.com` |
| `REDIS_URL` | Redis接続URL | （空） |
| `GOOGLE_SHEETS_ENABLED` | Google Sheets連携 | `False` |
| `GOOGLE_CREDENTIALS_JSON` | GCP認証情報 | （空） |

## ファイル構成

```
django_ats/
├── render.yaml          # Render Blueprint設定
├── build.sh             # ビルドスクリプト
├── requirements.txt     # Python依存関係
├── config/
│   └── settings/
│       ├── base.py      # 共通設定
│       ├── production.py # 本番設定（Render用）
│       └── development.py # 開発設定
└── staticfiles/         # 収集された静的ファイル
```

## ビルドプロセス

`build.sh`が以下を実行:

1. `pip install -r requirements.txt` - 依存関係インストール
2. `npm install` - Node.js依存関係（Tailwind CSS用）
3. `npm run build:css` - Tailwind CSSビルド
4. `python manage.py collectstatic` - 静的ファイル収集
5. `python manage.py migrate` - データベースマイグレーション
6. `python manage.py createcachetable` - キャッシュテーブル作成

## ヘルスチェック

Renderは `/health/` エンドポイントを定期的にチェックします。

```json
{
  "status": "healthy",
  "service": "django-ats"
}
```

## スケーリング

### Starterプラン（無料）
- RAM: 512MB
- CPU: 0.1 vCPU
- 月750時間無料

### Standardプラン（$7/月）
- RAM: 2GB
- CPU: 1 vCPU
- 常時稼働

## トラブルシューティング

### ビルドエラー

```bash
# ローカルでビルドスクリプトをテスト
chmod +x build.sh
./build.sh
```

### マイグレーションエラー

Renderのシェルから:
```bash
python manage.py migrate --no-input
```

### 静的ファイルが表示されない

1. `STATICFILES_STORAGE`が`whitenoise`に設定されているか確認
2. `collectstatic`が正常に完了したか確認

### データベース接続エラー

1. `DATABASE_URL`が正しく設定されているか確認
2. データベースが起動しているか確認

## 本番環境のセキュリティ

- `DEBUG=False`
- `SECRET_KEY`は必ず変更
- HTTPS強制（`SECURE_SSL_REDIRECT=True`）
- HSTS有効
- CSRFトークン検証

## 監視

### Sentry（推奨）

1. Sentryでプロジェクト作成
2. `SENTRY_DSN`環境変数を設定
3. エラーが自動的にSentryに送信される

### Renderログ

- Renderダッシュボードの「Logs」タブで確認
- `stdout`/`stderr`に出力されるログが表示される

## バックアップ

### データベース

Renderは自動バックアップを提供:
- Starter: 1日保持
- Standard: 7日保持

### 手動バックアップ

```bash
pg_dump $DATABASE_URL > backup.sql
```

## 料金

| リソース | プラン | 料金 |
|----------|--------|------|
| Web Service | Starter | 無料（月750時間） |
| Web Service | Standard | $7/月 |
| PostgreSQL | Starter | 無料（90日） |
| PostgreSQL | Standard | $7/月 |
| Redis | Starter | 無料 |
