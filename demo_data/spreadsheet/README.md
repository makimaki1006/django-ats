# ATS連携用スプレッドシート テストデータ

このフォルダには、ATSシステムのスプレッドシート連携用テストデータが含まれています。
`SPREADSHEET_SCHEMA.md` に完全準拠した形式です。

## シート構成

| シート名 | ファイル名 | カラム数 | データ件数 |
|---------|-----------|---------|-----------|
| 候補者 | 候補者.csv | 24 | 20件 |
| 求人 | 求人.csv | 21 | 10件 |
| 応募 | 応募.csv | 19 | 20件 |
| 面接 | 面接.csv | 20 | 12件 |
| 設定 | 設定.csv | 3 | 7件 |

## Google スプレッドシートへのインポート手順

### 方法1: シートごとにインポート（推奨）

1. Google スプレッドシートを新規作成
2. シート名を「候補者」に変更
3. `ファイル` → `インポート` → `アップロード`
4. `候補者.csv` を選択
5. 「現在のシートにデータを置換」を選択
6. 同様に「求人」「応募」「面接」「設定」シートを追加

### 方法2: Google Apps Scriptで自動作成

```javascript
function createDemoSpreadsheet() {
  // テンプレートをコピーして各CSVをインポート
  // （詳細は別途提供）
}
```

## カラム定義

### 候補者シート（24カラム）

| 列 | カラム名 | 説明 |
|----|---------|------|
| A | id | UUID（例: c001-0000-...） |
| B | name | 氏名 |
| C | name_kana | 氏名（かな） |
| D | email | メールアドレス |
| E | phone | 電話番号 |
| F | birth_date | 生年月日（YYYY-MM-DD） |
| G | gender | 性別（male/female/other） |
| H | postal_code | 郵便番号 |
| I | address | 住所 |
| J | current_company | 現在の勤務先 |
| K | current_position | 現在の役職 |
| L | years_of_experience | 経験年数 |
| M | desired_salary_min | 希望年収下限（万円） |
| N | desired_salary_max | 希望年収上限（万円） |
| O | desired_job_types | 希望職種（カンマ区切り） |
| P | skills | スキル（カンマ区切り） |
| Q | qualifications | 資格（カンマ区切り） |
| R | education | 最終学歴 |
| S | source | 流入経路 |
| T | status | ステータス |
| U | notes | 備考 |
| V | registered_by_id | 登録者ID |
| W | created_at | 作成日時（ISO 8601） |
| X | updated_at | 更新日時（ISO 8601） |

### 求人シート（21カラム）

| 列 | カラム名 | 説明 |
|----|---------|------|
| A | id | UUID |
| B | title | 求人タイトル |
| C | department | 部署 |
| D | employment_type | 雇用形態 |
| E | job_category | 職種カテゴリ |
| F | description | 仕事内容 |
| G | requirements | 応募要件 |
| H | preferred_skills | 歓迎スキル |
| I | salary_min | 給与下限（万円） |
| J | salary_max | 給与上限（万円） |
| K | work_location | 勤務地 |
| L | work_hours | 勤務時間 |
| M | benefits | 福利厚生 |
| N | number_of_positions | 募集人数 |
| O | status | ステータス |
| P | published_at | 公開日時 |
| Q | deadline | 応募締切 |
| R | notes | 備考 |
| S | created_by_id | 作成者ID |
| T | created_at | 作成日時 |
| U | updated_at | 更新日時 |

### 応募シート（19カラム）

| 列 | カラム名 | 説明 |
|----|---------|------|
| A | id | UUID |
| B | candidate_id | 候補者ID |
| C | candidate_name | 候補者名（表示用） |
| D | job_id | 求人ID |
| E | job_title | 求人タイトル（表示用） |
| F | status | ステータス |
| G | source | 応募経路 |
| H | applied_at | 応募日時 |
| I | evaluation_score | 評価スコア（1-5） |
| J | evaluation_notes | 評価コメント |
| K | offer_salary | 提示年収（万円） |
| L | offer_made_at | 内定日 |
| M | offer_deadline | 内定回答期限 |
| N | offer_notes | 内定条件メモ |
| O | joined_at | 入社日 |
| P | notes | 備考 |
| Q | registered_by_id | 登録者ID |
| R | created_at | 作成日時 |
| S | updated_at | 更新日時 |

### 面接シート（20カラム）

| 列 | カラム名 | 説明 |
|----|---------|------|
| A | id | UUID |
| B | application_id | 応募ID |
| C | candidate_name | 候補者名（表示用） |
| D | job_title | 求人タイトル（表示用） |
| E | interview_type | 面接種別 |
| F | round_number | 面接回数 |
| G | scheduled_at | 予定日時 |
| H | duration_minutes | 所要時間（分） |
| I | location | 場所 |
| J | meeting_url | オンラインURL |
| K | interviewer_ids | 面接官ID（カンマ区切り） |
| L | interviewer_names | 面接官名（カンマ区切り） |
| M | status | ステータス |
| N | result | 結果 |
| O | feedback | フィードバック |
| P | score | 評価スコア（1-5） |
| Q | notes | 備考 |
| R | created_by_id | 作成者ID |
| S | created_at | 作成日時 |
| T | updated_at | 更新日時 |

### 設定シート（3カラム）

| 列 | カラム名 | 説明 |
|----|---------|------|
| A | key | 設定キー |
| B | value | 設定値 |
| C | description | 説明 |

## ステータス値

### 候補者ステータス
- `new`: 新規
- `active`: アクティブ
- `in_process`: 選考中
- `hired`: 採用
- `rejected`: 不採用
- `withdrawn`: 辞退
- `inactive`: 非アクティブ

### 応募ステータス
- `new`: 新規応募
- `document_screening`: 書類選考中
- `document_passed`: 書類通過
- `document_rejected`: 書類不合格
- `interview_scheduled`: 面接調整中
- `interviewing`: 面接中
- `offer_pending`: 内定検討中
- `offer_made`: 内定
- `offer_accepted`: 内定承諾
- `offer_declined`: 内定辞退
- `rejected`: 不採用
- `withdrawn`: 辞退
- `on_hold`: 保留

### 面接ステータス
- `scheduled`: 予定
- `confirmed`: 確定
- `in_progress`: 実施中
- `completed`: 完了
- `cancelled`: キャンセル
- `no_show`: 欠席
- `rescheduled`: 日程変更

### 面接結果
- `passed`: 合格
- `failed`: 不合格
- `pending`: 保留

## データの特徴（介護・医療系）

### 求人職種
- 介護福祉士
- 看護師・准看護師
- ケアマネジャー
- 理学療法士・作業療法士・言語聴覚士
- 管理栄養士
- 夜勤専従スタッフ

### 応募経路
- 人材紹介会社（マイナビ介護、リクルートメディカル等）
- ハローワーク
- 自社採用サイト
- Indeed
- 大学・専門学校

### 応募ステータス分布
- 新規応募: 2件
- 書類選考中: 3件
- 書類通過: 3件
- 面接中: 5件
- 内定検討中: 2件
- 内定: 2件
- 内定承諾: 1件
- 不採用: 1件
- 辞退: 1件

## 注意事項

- 全てのデータはフィクションです
- メールアドレス・電話番号はダミーです
- 日付は2024年11月〜12月を想定しています
- ID形式は簡略化しています（本番はUUID v4）
