# Google Spreadsheet スキーマ設計書

## 概要

Django ATSでは、各テナント（顧客企業）ごとに1つのGoogle Spreadsheetを使用してデータを管理します。
このドキュメントでは、テンプレートスプレッドシートの構造と各シートのスキーマを定義します。

## テンプレートスプレッドシート構成

テンプレートは以下の5つのシートで構成されます：

| シート名 | 用途 | 行数目安 |
|---------|------|---------|
| 候補者 | 求職者情報 | ~1,000行 |
| 求人 | 求人票情報 | ~100行 |
| 応募 | 候補者×求人の紐付け | ~5,000行 |
| 面接 | 面接スケジュール・結果 | ~3,000行 |
| 設定 | テナント固有設定 | ~50行 |

---

## 1. 候補者シート

求職者の基本情報を管理します。

### カラム定義

| 列 | カラム名 | 型 | 必須 | 説明 |
|----|---------|-----|------|------|
| A | id | UUID | ○ | 一意識別子 |
| B | name | 文字列 | ○ | 氏名 |
| C | name_kana | 文字列 | | 氏名（かな） |
| D | email | 文字列 | ○ | メールアドレス |
| E | phone | 文字列 | | 電話番号 |
| F | birth_date | 日付 | | 生年月日（YYYY-MM-DD） |
| G | gender | 文字列 | | 性別（male/female/other） |
| H | postal_code | 文字列 | | 郵便番号 |
| I | address | 文字列 | | 住所 |
| J | current_company | 文字列 | | 現在の勤務先 |
| K | current_position | 文字列 | | 現在の役職 |
| L | years_of_experience | 数値 | | 経験年数 |
| M | desired_salary_min | 数値 | | 希望年収下限（万円） |
| N | desired_salary_max | 数値 | | 希望年収上限（万円） |
| O | desired_job_types | 文字列 | | 希望職種（カンマ区切り） |
| P | skills | 文字列 | | スキル（カンマ区切り） |
| Q | qualifications | 文字列 | | 資格（カンマ区切り） |
| R | education | 文字列 | | 最終学歴 |
| S | source | 文字列 | | 流入経路 |
| T | status | 文字列 | ○ | ステータス |
| U | notes | 文字列 | | 備考 |
| V | registered_by_id | UUID | | 登録者ID |
| W | created_at | 日時 | ○ | 作成日時（ISO 8601） |
| X | updated_at | 日時 | ○ | 更新日時（ISO 8601） |

### ステータス値

| 値 | 表示名 |
|----|-------|
| new | 新規 |
| active | アクティブ |
| in_process | 選考中 |
| hired | 採用 |
| rejected | 不採用 |
| withdrawn | 辞退 |
| inactive | 非アクティブ |

---

## 2. 求人シート

求人票の情報を管理します。

### カラム定義

| 列 | カラム名 | 型 | 必須 | 説明 |
|----|---------|-----|------|------|
| A | id | UUID | ○ | 一意識別子 |
| B | title | 文字列 | ○ | 求人タイトル |
| C | department | 文字列 | | 部署 |
| D | employment_type | 文字列 | | 雇用形態 |
| E | job_category | 文字列 | | 職種カテゴリ |
| F | description | 文字列 | | 仕事内容 |
| G | requirements | 文字列 | | 応募要件 |
| H | preferred_skills | 文字列 | | 歓迎スキル |
| I | salary_min | 数値 | | 給与下限（万円） |
| J | salary_max | 数値 | | 給与上限（万円） |
| K | work_location | 文字列 | | 勤務地 |
| L | work_hours | 文字列 | | 勤務時間 |
| M | benefits | 文字列 | | 福利厚生 |
| N | number_of_positions | 数値 | | 募集人数 |
| O | status | 文字列 | ○ | ステータス |
| P | published_at | 日時 | | 公開日時 |
| Q | deadline | 日付 | | 応募締切 |
| R | notes | 文字列 | | 備考 |
| S | created_by_id | UUID | | 作成者ID |
| T | created_at | 日時 | ○ | 作成日時 |
| U | updated_at | 日時 | ○ | 更新日時 |

### ステータス値

| 値 | 表示名 |
|----|-------|
| draft | 下書き |
| published | 公開中 |
| closed | 募集終了 |
| on_hold | 保留 |

### 雇用形態

| 値 | 表示名 |
|----|-------|
| full_time | 正社員 |
| contract | 契約社員 |
| part_time | パート・アルバイト |
| temporary | 派遣社員 |
| internship | インターン |

---

## 3. 応募シート

候補者と求人の紐付け（応募情報）を管理します。

### カラム定義

| 列 | カラム名 | 型 | 必須 | 説明 |
|----|---------|-----|------|------|
| A | id | UUID | ○ | 一意識別子 |
| B | candidate_id | UUID | ○ | 候補者ID |
| C | candidate_name | 文字列 | | 候補者名（表示用） |
| D | job_id | UUID | ○ | 求人ID |
| E | job_title | 文字列 | | 求人タイトル（表示用） |
| F | status | 文字列 | ○ | ステータス |
| G | source | 文字列 | | 応募経路 |
| H | applied_at | 日時 | ○ | 応募日時 |
| I | evaluation_score | 数値 | | 評価スコア（1-5） |
| J | evaluation_notes | 文字列 | | 評価コメント |
| K | offer_salary | 数値 | | 提示年収（万円） |
| L | offer_made_at | 日時 | | 内定日 |
| M | offer_deadline | 日付 | | 内定回答期限 |
| N | offer_notes | 文字列 | | 内定条件メモ |
| O | joined_at | 日付 | | 入社日 |
| P | notes | 文字列 | | 備考 |
| Q | registered_by_id | UUID | | 登録者ID |
| R | created_at | 日時 | ○ | 作成日時 |
| S | updated_at | 日時 | ○ | 更新日時 |

### ステータス値

| 値 | 表示名 |
|----|-------|
| new | 新規応募 |
| document_screening | 書類選考中 |
| document_passed | 書類通過 |
| document_rejected | 書類不合格 |
| interview_scheduled | 面接調整中 |
| interviewing | 面接中 |
| offer_pending | 内定検討中 |
| offer_made | 内定 |
| offer_accepted | 内定承諾 |
| offer_declined | 内定辞退 |
| rejected | 不採用 |
| withdrawn | 辞退 |
| on_hold | 保留 |

---

## 4. 面接シート

面接スケジュールと結果を管理します。

### カラム定義

| 列 | カラム名 | 型 | 必須 | 説明 |
|----|---------|-----|------|------|
| A | id | UUID | ○ | 一意識別子 |
| B | application_id | UUID | ○ | 応募ID |
| C | candidate_name | 文字列 | | 候補者名（表示用） |
| D | job_title | 文字列 | | 求人タイトル（表示用） |
| E | interview_type | 文字列 | | 面接種別 |
| F | round_number | 数値 | | 面接回数（1次、2次...） |
| G | scheduled_at | 日時 | | 予定日時 |
| H | duration_minutes | 数値 | | 所要時間（分） |
| I | location | 文字列 | | 場所 |
| J | meeting_url | 文字列 | | オンラインURL |
| K | interviewer_ids | 文字列 | | 面接官ID（カンマ区切り） |
| L | interviewer_names | 文字列 | | 面接官名（カンマ区切り） |
| M | status | 文字列 | ○ | ステータス |
| N | result | 文字列 | | 結果 |
| O | feedback | 文字列 | | フィードバック |
| P | score | 数値 | | 評価スコア（1-5） |
| Q | notes | 文字列 | | 備考 |
| R | created_by_id | UUID | | 作成者ID |
| S | created_at | 日時 | ○ | 作成日時 |
| T | updated_at | 日時 | ○ | 更新日時 |

### ステータス値

| 値 | 表示名 |
|----|-------|
| scheduled | 予定 |
| confirmed | 確定 |
| in_progress | 実施中 |
| completed | 完了 |
| cancelled | キャンセル |
| no_show | 欠席 |
| rescheduled | 日程変更 |

### 面接種別

| 値 | 表示名 |
|----|-------|
| phone | 電話面接 |
| video | ビデオ面接 |
| in_person | 対面面接 |
| group | グループ面接 |
| technical | 技術面接 |
| final | 最終面接 |

### 結果

| 値 | 表示名 |
|----|-------|
| passed | 合格 |
| failed | 不合格 |
| pending | 保留 |

---

## 5. 設定シート

テナント固有の設定値を管理します。

### カラム定義

| 列 | カラム名 | 型 | 説明 |
|----|---------|-----|------|
| A | key | 文字列 | 設定キー |
| B | value | 文字列 | 設定値 |
| C | description | 文字列 | 説明 |

### 初期設定値

| キー | 初期値 | 説明 |
|-----|-------|------|
| company_name | | 会社名 |
| timezone | Asia/Tokyo | タイムゾーン |
| date_format | YYYY-MM-DD | 日付形式 |
| currency | JPY | 通貨 |
| default_interview_duration | 60 | デフォルト面接時間（分） |
| notification_email | | 通知先メール |

---

## データ入力ガイドライン

### 日時形式
- ISO 8601形式を使用: `2025-12-27T10:30:00+09:00`
- 日付のみの場合: `2025-12-27`

### ID形式
- UUID v4形式: `550e8400-e29b-41d4-a716-446655440000`

### リスト形式
- カンマ区切りで格納: `Python, JavaScript, SQL`
- 前後の空白は自動トリム

### 空値の扱い
- 空文字列 `""` として格納
- 数値の空値は空文字列（0ではない）

---

## API制限への対応

### レート制限
- 300リクエスト/分/プロジェクト
- 60リクエスト/分/ユーザー

### 推奨事項
1. バッチ操作を使用（`append_rows`で一括追加）
2. キャッシュを活用（60秒TTL）
3. 不要な読み取りを避ける
4. エラー時は指数バックオフでリトライ

### パフォーマンス
- 1シートあたり5,000行以内を推奨
- 10万セル以上でパフォーマンス低下の可能性
- 大量データは定期的にアーカイブ

---

## テンプレート作成手順

1. Google Driveでスプレッドシートを新規作成
2. 上記5シートを追加（シート1をリネーム）
3. 各シートの1行目にヘッダーを設定
4. スプレッドシートIDを `GOOGLE_TEMPLATE_SPREADSHEET_ID` に設定
5. サービスアカウントにスプレッドシートを共有（編集権限）

---

## 関連ドキュメント

- [Google Sheets API ドキュメント](https://developers.google.com/sheets/api)
- [gspread ドキュメント](https://docs.gspread.org/)
- [Django ATS 設計書](./ARCHITECTURE.md)
