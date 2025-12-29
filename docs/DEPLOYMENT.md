# Django ATS - デプロイメントガイド

## 目次

1. [開発環境](#開発環境)
2. [本番環境](#本番環境)
3. [環境変数](#環境変数)
4. [SSL/TLS設定](#ssltls設定)
5. [バックアップ](#バックアップ)
6. [モニタリング](#モニタリング)

---

## 開発環境

### Docker Composeを使用した開発

```bash
# 開発環境の起動
docker-compose -f docker-compose.dev.yml up -d

# ログの確認
docker-compose -f docker-compose.dev.yml logs -f

# マイグレーション実行
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate

# スーパーユーザー作成
docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser

# 停止
docker-compose -f docker-compose.dev.yml down
```

### アクセス

- アプリケーション: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

---

## 本番環境

### 前提条件

- Docker 20.10+
- Docker Compose 2.0+
- ドメイン名（SSL用）

### デプロイ手順

1. **環境変数の設定**

```bash
cp .env.example .env
# .envを編集
nano .env
```

2. **Dockerイメージのビルド**

```bash
docker-compose build
```

3. **サービスの起動**

```bash
# 基本サービス（web, db, redis, celery）
docker-compose up -d

# Nginx込み（本番環境）
docker-compose --profile production up -d
```

4. **マイグレーション実行**

```bash
docker-compose exec web python manage.py migrate
```

5. **静的ファイルの収集**

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

6. **スーパーユーザー作成**

```bash
docker-compose exec web python manage.py createsuperuser
```

### ヘルスチェック

```bash
curl http://localhost:8000/health/
# {"status": "healthy", "database": "ok", "cache": "ok"}
```

---

## 環境変数

### 必須

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `SECRET_KEY` | Djangoシークレットキー | 50文字以上のランダム文字列 |
| `POSTGRES_PASSWORD` | PostgreSQLパスワード | 強力なパスワード |
| `ALLOWED_HOSTS` | 許可するホスト名 | `example.com,www.example.com` |

### オプション

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `DEBUG` | デバッグモード | `False` |
| `SENTRY_DSN` | Sentry DSN | なし |
| `REDIS_URL` | Redis接続URL | `redis://redis:6379/0` |

### シークレットキーの生成

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## SSL/TLS設定

### Let's Encryptを使用する場合

1. **証明書の取得**

```bash
# Certbotのインストール
apt install certbot

# 証明書の取得
certbot certonly --standalone -d example.com -d www.example.com
```

2. **証明書のコピー**

```bash
mkdir -p nginx/ssl
cp /etc/letsencrypt/live/example.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/example.com/privkey.pem nginx/ssl/
```

3. **Nginx設定の更新**

`nginx/conf.d/default.conf` のHTTPSセクションをコメント解除

4. **自動更新の設定**

```bash
# crontabに追加
0 0 1 * * certbot renew --quiet && docker-compose restart nginx
```

---

## バックアップ

### データベースバックアップ

```bash
# バックアップの作成
docker-compose exec db pg_dump -U postgres django_ats > backup_$(date +%Y%m%d).sql

# リストア
docker-compose exec -T db psql -U postgres django_ats < backup_YYYYMMDD.sql
```

### 自動バックアップスクリプト

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR=/path/to/backups
DATE=$(date +%Y%m%d_%H%M%S)

# データベースバックアップ
docker-compose exec -T db pg_dump -U postgres django_ats | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# メディアファイルバックアップ
tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C /path/to/media .

# 古いバックアップの削除（30日以上前）
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```

---

## モニタリング

### Sentryの設定

```bash
# .envに追加
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

### ログの確認

```bash
# 全サービスのログ
docker-compose logs -f

# 特定のサービスのログ
docker-compose logs -f web

# 最新100行のみ
docker-compose logs --tail=100 web
```

### リソース使用状況

```bash
docker stats
```

---

## トラブルシューティング

### よくある問題

1. **データベース接続エラー**
   - `docker-compose ps` でdbサービスの状態を確認
   - `docker-compose logs db` でエラーログを確認

2. **静的ファイルが表示されない**
   - `collectstatic` を再実行
   - Nginxの設定を確認

3. **メモリ不足**
   - `docker-compose down && docker system prune -a`
   - Docker Desktopのメモリ割り当てを増加

### サポート

問題が解決しない場合は、GitHubのIssueを作成してください。
