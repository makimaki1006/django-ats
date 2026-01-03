# UI/UX改善 作業計画書

**作成日**: 2026-01-03
**対象プロジェクト**: Django ATS
**総工数見積**: 約22時間

---

## 目次

1. [Phase 1: フォームUX改善](#phase-1-フォームux改善)
2. [Phase 2: HTMXインタラクション強化](#phase-2-htmxインタラクション強化)
3. [Phase 3: ダッシュボード可視化](#phase-3-ダッシュボード可視化)
4. [Phase 4: ローディング・状態表示](#phase-4-ローディング状態表示)
5. [Phase 5: アクセシビリティ改善](#phase-5-アクセシビリティ改善)
6. [Phase 6: カンバン・高度機能](#phase-6-カンバン高度機能)

---

## Phase 1: フォームUX改善

**工数**: 3.5時間
**優先度**: P1（最優先）

### 1.1 統一フォームフィールドコンポーネント作成

**タスク**:
- [ ] `templates/components/form_field.html` 作成
- [ ] `templates/components/form_errors.html` 作成
- [ ] 既存フォームテンプレートをリファクタリング

**実装内容**:
```
templates/components/
├── form_field.html      # 統一フィールドコンポーネント
├── form_errors.html     # エラー表示コンポーネント
└── form_section.html    # セクション見出しコンポーネント
```

**対象ファイル**:
- `templates/candidates/candidate_form.html`
- `templates/jobs/job_form.html`
- `templates/applications/application_form.html`
- `templates/interviews/interview_form.html`
- `templates/accounts/user_form.html`
- `templates/accounts/profile_form.html`

**動作確認方法**:
1. 各フォームページにアクセス
2. 必須フィールドを空のまま送信 → 全エラーが表示されることを確認
3. 複数フィールドにエラーがある場合、各フィールドに対応するエラーが表示されることを確認
4. help_textが適切に表示されることを確認

**テスト方法**:
```python
# tests/test_ui_forms.py
class FormComponentTest(TestCase):
    def test_form_field_renders_label(self):
        """フォームフィールドにラベルが表示される"""
        response = self.client.get(reverse('candidates:candidate_create'))
        self.assertContains(response, '<label')

    def test_form_shows_all_errors(self):
        """フォーム送信時に全エラーが表示される"""
        response = self.client.post(reverse('candidates:candidate_create'), {})
        self.assertContains(response, 'text-danger-600')
        # 複数のエラーメッセージが含まれることを確認
```

**Playwright E2Eテスト**:
```python
# e2e/test_form_ux.py
def test_form_error_display(page):
    page.goto("/candidates/create/")
    page.click("button[type=submit]")
    # 全エラーが表示されることを確認
    errors = page.locator(".text-danger-600")
    assert errors.count() >= 3  # 必須フィールド数以上
```

---

### 1.2 送信ボタンのローディング状態

**タスク**:
- [ ] 送信ボタンにHTMXローディング状態追加
- [ ] disabled状態のスタイリング
- [ ] スピナーアイコン統合

**実装内容**:
```html
<!-- 送信ボタンテンプレート -->
<button type="submit"
        class="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        hx-indicator="#submit-spinner">
    <span class="htmx-indicator" id="submit-spinner">
        <svg class="animate-spin h-4 w-4 mr-2">...</svg>
    </span>
    保存
</button>
```

**動作確認方法**:
1. フォーム送信ボタンをクリック
2. 送信中にボタンが無効化され、スピナーが表示されることを確認
3. 送信完了後、ボタンが元に戻ることを確認
4. 連打してもリクエストが重複しないことを確認

**テスト方法**:
```python
# Playwright
def test_submit_button_loading_state(page):
    page.goto("/candidates/create/")
    # フォーム入力
    page.fill("input[name=name]", "テスト太郎")
    page.fill("input[name=email]", "test@example.com")

    # 送信クリック
    page.click("button[type=submit]")

    # ローディング中はボタンが無効化
    assert page.locator("button[type=submit]").is_disabled()
```

---

### 1.3 Empty Stateパーシャル化

**タスク**:
- [ ] `templates/components/empty_state.html` 作成
- [ ] 各リストページで使用
- [ ] アイコン・メッセージ・CTAをパラメータ化

**対象ファイル**:
- `templates/candidates/candidate_list.html`
- `templates/applications/application_list.html`
- `templates/jobs/job_list.html`
- `templates/interviews/interview_list.html`

**動作確認方法**:
1. 空のテナントでログイン
2. 各リストページにアクセス
3. 適切なEmpty Stateが表示されることを確認
4. CTAボタンが正しいURLにリンクしていることを確認

**テスト方法**:
```python
def test_empty_state_display(self):
    """データがない場合にEmpty Stateが表示される"""
    response = self.client.get(reverse('candidates:candidate_list'))
    self.assertContains(response, '候補者がいません')
    self.assertContains(response, 'href="/candidates/create/"')
```

---

## Phase 2: HTMXインタラクション強化

**工数**: 5時間
**優先度**: P1

### 2.1 ページネーションAJAX化

**タスク**:
- [ ] リストテーブルにID付与
- [ ] ページネーションリンクをhx-get化
- [ ] URL履歴の更新（hx-push-url）

**対象ファイル**:
- `templates/candidates/candidate_list.html`
- `templates/applications/application_list.html`
- `templates/jobs/job_list.html`
- `templates/interviews/interview_list.html`
- `templates/accounts/user_list.html`
- `templates/accounts/audit_log_list.html`
- `templates/accounts/login_history_list.html`

**実装内容**:
```html
<!-- リストコンテナ -->
<div id="list-container">
    {% include "candidates/partials/candidate_table.html" %}
</div>

<!-- ページネーション -->
<a hx-get="?page={{ page_obj.next_page_number }}"
   hx-target="#list-container"
   hx-swap="innerHTML"
   hx-push-url="true"
   class="...">次へ</a>
```

**パーシャルテンプレート作成**:
```
templates/candidates/partials/
├── candidate_table.html      # テーブル本体
└── candidate_pagination.html # ページネーション
```

**動作確認方法**:
1. リストページにアクセス
2. 「次へ」をクリック → ページ全体がリロードせずテーブルのみ更新
3. ブラウザの戻るボタンで前ページに戻れることを確認
4. URLが正しく更新されていることを確認

**テスト方法**:
```python
# Playwright
def test_ajax_pagination(page):
    page.goto("/candidates/")

    # 初回ロード時のリクエスト数を記録
    initial_requests = len(page.context.requests)

    # 次ページクリック
    page.click("a:has-text('次へ')")
    page.wait_for_load_state("networkidle")

    # フルリロードではないことを確認（リクエストが少ない）
    # URLが更新されていることを確認
    assert "page=2" in page.url
```

---

### 2.2 リアルタイムフィルター

**タスク**:
- [ ] 検索入力にhx-triggerでdebounce追加
- [ ] フィルターセレクトにchange時の自動送信
- [ ] フィルター結果のURL反映

**実装内容**:
```html
<!-- 検索フィールド -->
<input type="text" name="q"
       hx-get="{% url 'candidates:candidate_list' %}"
       hx-trigger="keyup changed delay:500ms"
       hx-target="#list-container"
       hx-push-url="true"
       placeholder="検索...">

<!-- フィルターセレクト -->
<select name="status"
        hx-get="{% url 'candidates:candidate_list' %}"
        hx-trigger="change"
        hx-target="#list-container"
        hx-include="[name='q']">
    ...
</select>
```

**動作確認方法**:
1. 検索フィールドに文字入力
2. 500ms後に自動で検索が実行されることを確認
3. フィルタードロップダウン変更時に即座にフィルタリング
4. 検索とフィルターが組み合わせ可能なことを確認

**テスト方法**:
```python
def test_realtime_search(page):
    page.goto("/candidates/")
    page.fill("input[name=q]", "田中")
    # 500ms待機
    page.wait_for_timeout(600)
    # 結果が更新されていることを確認
    assert "田中" in page.content()
```

---

### 2.3 HTMXエラーハンドリング改善

**タスク**:
- [ ] ステータスコード別エラーメッセージ
- [ ] トースト通知の自動非表示
- [ ] オフライン検出

**実装内容**:
```javascript
// base.html に追加
document.body.addEventListener('htmx:responseError', function(evt) {
    const status = evt.detail.xhr.status;
    let message = 'エラーが発生しました';
    let type = 'error';

    switch(status) {
        case 400: message = '入力内容に問題があります'; break;
        case 403: message = 'アクセス権限がありません'; break;
        case 404: message = 'ページが見つかりません'; break;
        case 500: message = 'サーバーエラーが発生しました'; break;
    }

    showToast(message, type);
});

// オフライン検出
window.addEventListener('offline', () => {
    showToast('インターネット接続が切断されました', 'warning');
});
```

**動作確認方法**:
1. 存在しないURLへのHTMXリクエスト → 404メッセージ表示
2. 権限のないページへアクセス → 403メッセージ表示
3. ネットワーク切断 → オフライン警告表示
4. トーストが5秒後に自動で消えることを確認

**テスト方法**:
```python
def test_htmx_error_handling(page):
    page.goto("/candidates/")
    # 存在しないページへのリクエストをシミュレート
    page.evaluate("""
        htmx.ajax('GET', '/non-existent/', {target: '#list-container'})
    """)
    # エラートーストが表示されることを確認
    assert page.locator(".toast-error").is_visible()
```

---

## Phase 3: ダッシュボード可視化

**工数**: 5時間
**優先度**: P2

### 3.1 Chart.js統合

**タスク**:
- [ ] Chart.js CDN追加（または npm install）
- [ ] チャートコンポーネント作成
- [ ] ダッシュボードビューでデータをJSON出力

**実装内容**:
```html
<!-- base.html に追加 -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- templates/components/charts/ -->
├── line_chart.html
├── bar_chart.html
├── doughnut_chart.html
└── funnel_chart.html
```

**動作確認方法**:
1. ダッシュボードにアクセス
2. 月別トレンドがラインチャートで表示されることを確認
3. ファネルがビジュアルで表示されることを確認
4. ホバーで詳細データが表示されることを確認

---

### 3.2 月別トレンドチャート

**タスク**:
- [ ] `DashboardView`にチャートデータ追加
- [ ] `templates/core/dashboard.html`にチャート埋め込み
- [ ] レスポンシブ対応

**実装内容**:
```python
# views.py
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)

    # 月別データをJSON形式で
    monthly_data = self.get_monthly_trend()
    context['chart_data'] = json.dumps({
        'labels': [m['month'] for m in monthly_data],
        'applications': [m['applications'] for m in monthly_data],
        'hired': [m['hired'] for m in monthly_data],
    })
    return context
```

```html
<!-- dashboard.html -->
<canvas id="monthly-trend-chart"></canvas>
<script>
const ctx = document.getElementById('monthly-trend-chart');
new Chart(ctx, {
    type: 'line',
    data: {
        labels: {{ chart_data.labels|safe }},
        datasets: [{
            label: '応募数',
            data: {{ chart_data.applications|safe }},
            borderColor: 'rgb(59, 130, 246)',
        }, {
            label: '採用数',
            data: {{ chart_data.hired|safe }},
            borderColor: 'rgb(34, 197, 94)',
        }]
    }
});
</script>
```

**動作確認方法**:
1. ダッシュボードで月別トレンドチャートが表示される
2. 応募数と採用数の2つのラインが表示される
3. ホバーで具体的な数値が表示される
4. モバイルでも正しく表示される

**テスト方法**:
```python
def test_dashboard_chart_data(self):
    """ダッシュボードにチャートデータが含まれる"""
    response = self.client.get(reverse('core:dashboard'))
    self.assertIn('chart_data', response.context)

def test_chart_renders(page):
    page.goto("/dashboard/")
    # Canvas要素が存在
    assert page.locator("#monthly-trend-chart").is_visible()
```

---

### 3.3 採用ファネルチャート

**タスク**:
- [ ] ファネル用のデータ集計
- [ ] ファネルチャートコンポーネント作成
- [ ] ステージごとの色分け

**実装内容**:
```html
<!-- ファネルチャート（水平バーチャート） -->
<canvas id="funnel-chart"></canvas>
<script>
new Chart(document.getElementById('funnel-chart'), {
    type: 'bar',
    data: {
        labels: ['応募', '書類選考', '一次面接', '最終面接', '内定', '入社'],
        datasets: [{
            data: [100, 80, 50, 30, 15, 10],
            backgroundColor: [
                '#3B82F6', '#60A5FA', '#93C5FD',
                '#10B981', '#34D399', '#6EE7B7'
            ],
        }]
    },
    options: {
        indexAxis: 'y',
        plugins: {
            legend: { display: false }
        }
    }
});
</script>
```

**動作確認方法**:
1. ファネルチャートが横棒グラフで表示される
2. 各ステージの数値が表示される
3. 色がステージごとに異なる

---

## Phase 4: ローディング・状態表示

**工数**: 4時間
**優先度**: P2

### 4.1 Skeletonローダー実装

**タスク**:
- [ ] 既存`skeleton.html`の活用
- [ ] 初期ロード時のSkeleton表示
- [ ] HTMXリクエスト中のSkeleton表示

**対象ファイル**:
- `templates/components/skeleton.html`（既存）
- 各リストページ

**実装内容**:
```html
<!-- candidate_list.html -->
<div id="list-container"
     hx-get="{% url 'candidates:candidate_list' %}"
     hx-trigger="load"
     hx-swap="innerHTML">
    <!-- 初期表示はSkeleton -->
    {% include "components/skeleton.html" with type="table-row" count=10 %}
</div>
```

**動作確認方法**:
1. リストページにアクセス
2. データロード中にSkeletonが表示される
3. データロード完了後、実データに置き換わる
4. ページネーション時もSkeletonが表示される

**テスト方法**:
```python
def test_skeleton_loader(page):
    # ネットワークを遅延させる
    page.route("**/*", lambda route: route.continue_(delay=1000))
    page.goto("/candidates/")
    # Skeletonが表示されていることを確認
    assert page.locator(".animate-pulse").count() > 0
```

---

### 4.2 トースト通知システム改善

**タスク**:
- [ ] トーストコンポーネントの統一
- [ ] 複数トーストのスタック表示
- [ ] アニメーション追加（スライドイン/アウト）

**実装内容**:
```html
<!-- templates/components/toast.html -->
<div id="toast-container"
     class="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
</div>

<script>
function showToast(message, type = 'info', duration = 5000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} transform translate-x-full transition-transform`;
    toast.innerHTML = `
        <div class="flex items-center p-4 rounded-lg shadow-lg ${getToastColor(type)}">
            ${getToastIcon(type)}
            <span class="ml-3 text-sm">${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-auto">
                <svg class="h-4 w-4">...</svg>
            </button>
        </div>
    `;
    container.appendChild(toast);

    // スライドインアニメーション
    requestAnimationFrame(() => {
        toast.classList.remove('translate-x-full');
    });

    // 自動非表示
    setTimeout(() => {
        toast.classList.add('translate-x-full');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}
</script>
```

**動作確認方法**:
1. 操作成功時に緑色のトーストが表示される
2. エラー時に赤色のトーストが表示される
3. 複数のトーストが重ならずスタック表示される
4. 5秒後に自動で消える、または×ボタンで閉じられる

---

### 4.3 プログレスインジケーター

**タスク**:
- [ ] ページ上部にプログレスバー追加
- [ ] HTMXリクエスト中に表示
- [ ] NProgress.js または カスタム実装

**実装内容**:
```html
<!-- base.html -->
<div id="progress-bar"
     class="fixed top-0 left-0 h-1 bg-blue-600 z-50 transition-all duration-300"
     style="width: 0%"></div>

<script>
document.body.addEventListener('htmx:beforeRequest', () => {
    document.getElementById('progress-bar').style.width = '30%';
});
document.body.addEventListener('htmx:afterRequest', () => {
    const bar = document.getElementById('progress-bar');
    bar.style.width = '100%';
    setTimeout(() => bar.style.width = '0%', 300);
});
</script>
```

**動作確認方法**:
1. HTMXリクエスト開始時にプログレスバーが表示される
2. リクエスト完了時に100%になり、その後消える
3. 複数のリクエストが同時に発生しても正しく動作する

---

## Phase 5: アクセシビリティ改善

**工数**: 3時間
**優先度**: P2

### 5.1 ARIAラベル追加

**タスク**:
- [ ] 全ボタンにaria-label追加
- [ ] アバター画像にalt追加
- [ ] アイコンボタンにsr-only追加

**対象ファイル**:
- `templates/components/navbar.html`
- `templates/components/sidebar.html`
- 各リスト・詳細テンプレート

**実装内容**:
```html
<!-- Before -->
<button class="...">
    <svg>...</svg>
</button>

<!-- After -->
<button class="..." aria-label="メニューを開く">
    <svg aria-hidden="true">...</svg>
    <span class="sr-only">メニューを開く</span>
</button>

<!-- アバター -->
<img src="..." alt="{{ user.name }}のプロフィール画像" class="...">
```

**動作確認方法**:
1. スクリーンリーダー（NVDA/VoiceOver）で全ページを確認
2. 全てのインタラクティブ要素が読み上げられることを確認
3. アイコンのみのボタンに適切なラベルがあることを確認

**テスト方法**:
```python
def test_aria_labels(page):
    page.goto("/candidates/")
    # 全ボタンにaria-labelがあることを確認
    buttons = page.locator("button")
    for i in range(buttons.count()):
        btn = buttons.nth(i)
        assert btn.get_attribute("aria-label") or btn.inner_text().strip()
```

---

### 5.2 キーボードナビゲーション

**タスク**:
- [ ] ドロップダウンでfocus trap実装
- [ ] Escキーでモーダル/ドロップダウン閉じる
- [ ] Tab順序の最適化

**実装内容**:
```javascript
// ドロップダウンのキーボード操作
document.querySelectorAll('[data-dropdown]').forEach(dropdown => {
    dropdown.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            dropdown.close();
        }
        if (e.key === 'ArrowDown') {
            // 次の項目にフォーカス
        }
        if (e.key === 'ArrowUp') {
            // 前の項目にフォーカス
        }
    });
});
```

**動作確認方法**:
1. Tabキーのみで全ページをナビゲートできることを確認
2. ドロップダウン内で矢印キーで移動できることを確認
3. Escキーでモーダル/ドロップダウンが閉じることを確認

---

### 5.3 カラーコントラスト改善

**タスク**:
- [ ] 色のみで情報を伝えている箇所にアイコン/テキスト追加
- [ ] コントラスト比の確認（WCAG AA: 4.5:1以上）

**対象箇所**:
- 経過日数の色分け（application_list.html）
- ステータスバッジ
- エラーメッセージ

**実装内容**:
```html
<!-- Before: 色のみ -->
<span class="text-danger-600">7日</span>

<!-- After: 色 + アイコン + aria-label -->
<span class="text-danger-600 font-semibold"
      aria-label="応募から7日経過 - 早期対応が必要">
    <svg class="inline h-4 w-4 mr-1" aria-hidden="true">⚠️</svg>
    7日
</span>
```

**動作確認方法**:
1. Chrome DevToolsのAccessibility検査を実行
2. コントラスト警告がないことを確認
3. 色覚シミュレーターで確認

---

## Phase 6: カンバン・高度機能

**工数**: 6時間
**優先度**: P3

### 6.1 カンバンDrag & Drop

**タスク**:
- [ ] Sortable.js導入
- [ ] カンバンカードのドラッグ操作
- [ ] ステータス変更APIエンドポイント作成
- [ ] HTMXでステータス更新

**実装内容**:
```html
<!-- application_kanban.html -->
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>

<div class="kanban-board flex gap-4 overflow-x-auto">
    {% for status in statuses %}
    <div class="kanban-column w-80 bg-gray-100 rounded-lg p-4"
         data-status="{{ status.value }}"
         id="column-{{ status.value }}">
        <h3 class="font-semibold mb-4">{{ status.label }}</h3>
        <div class="kanban-cards space-y-2" data-sortable>
            {% for app in applications|filter_status:status.value %}
            <div class="kanban-card bg-white p-3 rounded shadow cursor-move"
                 data-id="{{ app.id }}"
                 draggable="true">
                {{ app.candidate.name }}
            </div>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
</div>

<script>
document.querySelectorAll('[data-sortable]').forEach(el => {
    new Sortable(el, {
        group: 'kanban',
        animation: 150,
        onEnd: function(evt) {
            const appId = evt.item.dataset.id;
            const newStatus = evt.to.closest('.kanban-column').dataset.status;

            htmx.ajax('PATCH', `/api/applications/${appId}/status/`, {
                values: { status: newStatus },
                target: evt.item,
            });
        }
    });
});
</script>
```

**動作確認方法**:
1. カンバンボードでカードをドラッグできることを確認
2. 別のカラムにドロップするとステータスが変更されることを確認
3. ページリロード後も変更が保持されていることを確認
4. 同時編集時の競合が適切に処理されることを確認

**テスト方法**:
```python
# E2Eテスト
def test_kanban_drag_drop(page):
    page.goto("/applications/kanban/")

    # カードをドラッグ
    card = page.locator(".kanban-card").first
    target = page.locator("#column-interview")

    card.drag_to(target)

    # ステータスが更新されたことを確認
    page.reload()
    assert page.locator("#column-interview .kanban-card").count() > 0
```

---

### 6.2 クイックアクション

**タスク**:
- [ ] リスト行のホバーでアクションボタン表示
- [ ] ワンクリックでステータス変更
- [ ] キーボードショートカット

**実装内容**:
```html
<!-- リスト行 -->
<tr class="group hover:bg-gray-50">
    <td>...</td>
    <td class="relative">
        <div class="opacity-0 group-hover:opacity-100 transition-opacity">
            <button hx-patch="/applications/{{ app.id }}/quick-status/"
                    hx-vals='{"status": "interview"}'
                    class="btn-sm">
                面接へ
            </button>
        </div>
    </td>
</tr>
```

**動作確認方法**:
1. リスト行にホバーするとアクションボタンが表示される
2. ボタンクリックで即座にステータスが変更される
3. キーボードでも操作可能

---

## テスト計画

### ユニットテスト

```python
# tests/test_ui_components.py

class FormComponentTests(TestCase):
    """フォームコンポーネントのテスト"""

    def test_form_field_renders_correctly(self):
        pass

    def test_form_errors_display_all(self):
        pass

    def test_empty_state_renders(self):
        pass

class ChartDataTests(TestCase):
    """チャートデータのテスト"""

    def test_monthly_trend_data(self):
        pass

    def test_funnel_data(self):
        pass
```

### E2Eテスト（Playwright）

```python
# e2e/test_ui_ux.py

class TestFormUX:
    def test_form_validation(self, page):
        pass

    def test_submit_loading_state(self, page):
        pass

class TestListInteraction:
    def test_ajax_pagination(self, page):
        pass

    def test_realtime_filter(self, page):
        pass

class TestDashboard:
    def test_charts_render(self, page):
        pass

class TestAccessibility:
    def test_keyboard_navigation(self, page):
        pass

    def test_aria_labels(self, page):
        pass
```

---

## 完了基準

### Phase 1 完了基準
- [ ] 全フォームで統一されたエラー表示
- [ ] 送信ボタンのローディング状態が動作
- [ ] Empty Stateが全リストページで統一

### Phase 2 完了基準
- [ ] ページネーションがAJAXで動作
- [ ] リアルタイムフィルターが500ms debounceで動作
- [ ] エラートーストがステータスコード別に表示

### Phase 3 完了基準
- [ ] 月別トレンドがラインチャートで表示
- [ ] 採用ファネルがビジュアルで表示
- [ ] モバイルでもチャートが正しく表示

### Phase 4 完了基準
- [ ] Skeletonローダーがデータロード中に表示
- [ ] トースト通知がスタック表示
- [ ] プログレスバーがHTMXリクエスト中に表示

### Phase 5 完了基準
- [ ] 全インタラクティブ要素にARIAラベル
- [ ] キーボードのみで全機能にアクセス可能
- [ ] WCAGアクセシビリティ検査に合格

### Phase 6 完了基準
- [ ] カンバンでDrag & Dropが動作
- [ ] ステータス変更がDBに保存
- [ ] クイックアクションが動作

---

## 実行スケジュール（推奨）

| Phase | 内容 | 工数 | 累計 |
|-------|------|------|------|
| 1 | フォームUX改善 | 3.5h | 3.5h |
| 2 | HTMXインタラクション | 5h | 8.5h |
| 3 | ダッシュボード可視化 | 5h | 13.5h |
| 4 | ローディング・状態表示 | 4h | 17.5h |
| 5 | アクセシビリティ | 3h | 20.5h |
| 6 | カンバン・高度機能 | 6h | 26.5h |

**総工数**: 約26.5時間（バッファ含む）

---

## 備考

- 各Phaseは独立して実装可能
- P1（Phase 1-2）を先に完了させることで、即座にUX改善効果が得られる
- Chart.jsは軽量なためCDN利用を推奨
- Sortable.jsはカンバン機能のみで使用

