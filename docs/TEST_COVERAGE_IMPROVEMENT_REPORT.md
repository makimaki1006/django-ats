# テストカバレッジ改善レポート

**作成日**: 2025-12-28
**最終更新**: 2026-01-09
**バージョン**: 1.1
**ステータス**: 完了

---

## 1. エグゼクティブサマリー

| メトリクス | 開始時 | 中間 | 最新 |
|-----------|--------|--------|------|
| テスト数 | 970 | 998 | 1,143 |
| カバレッジ | 94% | 95% | 95% |
| 未カバー行 | ~174 | 140 | ~140 |
| 失敗テスト | 0 | 0 | 0 |
| 本番バグ発見 | - | 3件 | 3件 |

**総評**: テストカバレッジ95%を維持。テスト数は1,143に増加。テスト作成中に本番コードの重大バグを3件発見・修正。

---

## 2. 追加されたテストファイル

### 2.1 test_candidates_models_full.py

**目的**: candidates/models.pyの完全カバレッジ

**テストクラス**:
- `TestCandidateModelProperties` (11テスト)
  - `test_get_absolute_url`: URL生成
  - `test_age_with_birthdate`: 年齢計算（生年月日あり）
  - `test_age_without_birthdate`: 年齢計算（生年月日なし）
  - `test_age_birthday_not_yet`: 誕生日未到来ケース
  - `test_has_resume_true/false`: 履歴書有無
  - `test_is_from_agent_true/false`: エージェント経由判定
  - `test_active_applications_count_*`: 進行中応募数計算

- `TestCandidateManagerFull` (1テスト)
  - `test_get_for_user_agent_without_company`: エージェント未設定ユーザー

- `TestCandidateCommentModel` (16テスト)
  - `test_str_*`: __str__メソッド
  - `test_is_edited_*`: 編集済みフラグ
  - `test_last_edited_at_*`: 最終編集日時
  - `test_edit_*`: 編集機能
  - `test_soft_delete_*`: 論理削除
  - `test_can_edit_*`: 編集権限判定
  - `test_can_delete_*`: 削除権限判定

### 2.2 test_interviews_models_full.py

**目的**: interviews/models.pyの完全カバレッジ

**テストクラス**:
- `TestInterviewModelProperties` (12テスト)
  - `test_get_absolute_url`: URL生成
  - `test_get_interview_round_display_*`: 面接回数表示
  - `test_is_upcoming_*`: 今後の面接判定
  - `test_is_today_*`: 本日面接判定
  - `test_candidate_property`: 候補者ショートカット
  - `test_job_property`: 求人ショートカット
  - `test_actual_duration_minutes_*`: 実際の面接時間計算

- `TestInterviewModelMethods` (3テスト)
  - `test_complete`: 面接完了処理
  - `test_complete_with_existing_ended_at`: 終了時刻既存ケース
  - `test_cancel`: キャンセル処理

- `TestInterviewFeedbackRequestModel` (2テスト)
  - `test_str`: __str__メソッド
  - `test_submit`: フィードバック提出

### 2.3 test_jobs_views_full.py

**目的**: jobs/views.pyのビュー層テスト

**テストクラス**:
- `TestJobCreateViewFull` (3テスト)
- `TestJobUpdateViewFull` (3テスト)
- `TestJobListViewFull` (2テスト)
- `TestJobDetailViewFull` (2テスト)
- `TestJobStatusChangeViewFull` (2テスト)

---

## 3. 発見・修正されたバグ

### 3.1 active_applications_countの日本語ラベルバグ

**ファイル**: `apps/candidates/models.py:384-386`

**問題コード**:
```python
@property
def active_applications_count(self):
    return self.applications.exclude(
        status__in=['不採用', '辞退', '内定辞退']  # ← 日本語ラベル
    ).count()
```

**影響**: ApplicationStatusChoicesは英語値（'rejected', 'withdrawn', 'offer_declined'）を使用するため、フィルタリングが機能せず、**全ての応募が「進行中」としてカウントされていた**。

**修正コード**:
```python
@property
def active_applications_count(self):
    from apps.applications.models import ApplicationStatusChoices
    return self.applications.exclude(
        status__in=[
            ApplicationStatusChoices.REJECTED,
            ApplicationStatusChoices.WITHDRAWN,
            ApplicationStatusChoices.OFFER_DECLINED
        ]
    ).count()
```

**深刻度**: High（本番データ表示に影響）

---

### 3.2 Candidate.get_absolute_urlのURL名誤り

**ファイル**: `apps/candidates/models.py:357`

**問題コード**:
```python
def get_absolute_url(self):
    return reverse('candidates:detail', kwargs={'pk': self.pk})
```

**影響**: `candidates:detail`というURL名は存在せず、`candidates:candidate_detail`が正しい。テンプレート内で`get_absolute_url`を使用するとNoReverseMatchエラーが発生。

**修正コード**:
```python
def get_absolute_url(self):
    return reverse('candidates:candidate_detail', kwargs={'pk': self.pk})
```

**深刻度**: Medium（リンク生成時にエラー）

---

### 3.3 Interview.get_absolute_urlのURL名誤り

**ファイル**: `apps/interviews/models.py:190`

**問題コード**:
```python
def get_absolute_url(self):
    return reverse('interviews:detail', kwargs={'pk': self.pk})
```

**影響**: 3.2と同様、`interviews:interview_detail`が正しいURL名。

**修正コード**:
```python
def get_absolute_url(self):
    return reverse('interviews:interview_detail', kwargs={'pk': self.pk})
```

**深刻度**: Medium（リンク生成時にエラー）

---

## 4. テスト品質評価

### 4.1 良好な点

| 項目 | 評価 | 詳細 |
|------|------|------|
| ビジネスロジックカバー | A | モデルメソッド（edit, soft_delete, complete, cancel）を網羅 |
| エッジケース考慮 | A | 誕生日の年またぎ、権限エラー、空クエリセット等 |
| 認証統合テスト | A | force_loginによる実際の認証フロー検証 |
| 命名規則 | A | 日本語docstringで目的が明確 |

### 4.2 改善の余地

| 項目 | 評価 | 詳細 |
|------|------|------|
| View form_validテスト | B | テナントミドルウェアのモックが必要 |
| 抽象クラステスト | N/A | SoftDeleteModelは具象クラスでテスト |

---

## 5. 未カバーコード分析

### 5.1 残り140行の内訳

| カテゴリ | 行数 | 正当性 | 推奨アクション |
|---------|------|--------|----------------|
| 抽象クラスメソッド（SoftDeleteModel） | ~8 | 正当 | 具象モデルでテスト済み |
| View form_validメソッド | ~11 | テスト可能 | ミドルウェアモック追加 |
| 管理画面関連 | ~20 | 低優先度 | 必要に応じて追加 |
| 例外ハンドリング分岐 | ~100 | 一部テスト可能 | 優先度に応じて |

### 5.2 100%達成への推奨事項

1. **テナントミドルウェアのモック**
   ```python
   from unittest.mock import patch

   @patch('apps.core.middleware.TenantMiddleware.process_request')
   def test_form_valid(self, mock_middleware, client, admin_user):
       mock_middleware.return_value = None
       # テスト実行
   ```

2. **管理画面テストの追加**（必要に応じて）

---

## 6. 実行方法

### 6.1 全テスト実行
```bash
cd django_ats
python -m pytest
```

### 6.2 カバレッジレポート生成
```bash
python -m pytest --cov=apps --cov-report=html
```

### 6.3 特定テストファイル実行
```bash
python -m pytest tests/test_candidates_models_full.py -v
python -m pytest tests/test_interviews_models_full.py -v
python -m pytest tests/test_jobs_views_full.py -v
```

---

## 7. 結論

テストカバレッジ改善作業により:

1. **品質向上**: テスト数 970 → 1,143（+173テスト）、カバレッジ94%→95%
2. **バグ発見**: 本番影響のあるバグ3件を発見・修正
3. **回帰防止**: 1,143テストによる堅牢な品質ゲート確立

特に`active_applications_count`のバグは本番データ表示に直接影響するため、早期発見・修正の価値が高い。

---

## 8. 更新履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2025-12-28 | 1.0 | 初版作成 |
| 2026-01-09 | 1.1 | テスト数を1,143に更新、本番デプロイ反映 |
