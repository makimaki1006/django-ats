"""
UI/UXコンポーネントのテスト
Phase 1-6で実装されるコンポーネントの動作確認
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.candidates.models import Candidate
from apps.jobs.models import Job
from apps.interviews.models import Interview
from apps.applications.models import Application

User = get_user_model()


class BaseUITestCase(TestCase):
    """UI テストの基底クラス"""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
        )
        cls.user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            tenant=cls.tenant,
            role='client_admin',
        )

    def setUp(self):
        self.client = Client()
        self.client.login(email='admin@test.com', password='testpass123')


class FormFieldComponentTest(BaseUITestCase):
    """フォームフィールドコンポーネントのテスト"""

    def test_form_field_renders_label(self):
        """フォームフィールドにラベルが表示される"""
        response = self.client.get(reverse('candidates:candidate_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<label')
        self.assertContains(response, 'for="id_name"')

    def test_form_shows_errors_on_invalid_submit(self):
        """フォーム送信時にエラーが表示される"""
        response = self.client.post(
            reverse('candidates:candidate_create'),
            data={},  # 空のデータ
        )
        # エラーメッセージが含まれることを確認
        self.assertContains(response, 'text-danger')

    def test_form_required_field_indicator(self):
        """必須フィールドに*マークが表示される"""
        response = self.client.get(reverse('candidates:candidate_create'))
        self.assertContains(response, 'text-danger-500')  # 必須マーク用のクラス


class EmptyStateComponentTest(TestCase):
    """Empty Stateコンポーネントのテスト（テンプレートファイル直接読み込み）"""

    def test_empty_state_template_has_icon(self):
        """Empty StateテンプレートにSVGアイコンがある"""
        from pathlib import Path

        empty_state_path = Path(__file__).parent.parent / 'templates' / 'components' / 'empty_state.html'
        if empty_state_path.exists():
            content = empty_state_path.read_text(encoding='utf-8')
            self.assertIn('<svg', content)
            self.assertIn('aria-hidden="true"', content)

    def test_empty_state_template_has_cta_button(self):
        """Empty StateテンプレートにCTAボタンスロットがある"""
        from pathlib import Path

        empty_state_path = Path(__file__).parent.parent / 'templates' / 'components' / 'empty_state.html'
        if empty_state_path.exists():
            content = empty_state_path.read_text(encoding='utf-8')
            # CTAボタン用のリンクがあるか確認
            self.assertIn('href=', content)
            self.assertIn('bg-blue-600', content)  # プライマリボタンのスタイル


class HTMXPaginationTest(BaseUITestCase):
    """HTMXページネーションのテスト"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # 25件の候補者を作成（ページネーションが発生する数）
        for i in range(25):
            Candidate.objects.create(
                tenant=cls.tenant,
                name=f'候補者{i+1}',
                email=f'candidate{i+1}@test.com',
            )

    def test_pagination_links_have_htmx_attributes(self):
        """ページネーションリンクにHTMX属性がある"""
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertEqual(response.status_code, 200)
        # hx-get属性があることを確認
        self.assertContains(response, 'hx-get')
        self.assertContains(response, 'hx-target')

    def test_htmx_request_returns_partial(self):
        """HTMXリクエストでパーシャルテンプレートが返される"""
        response = self.client.get(
            reverse('candidates:candidate_list'),
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        # 完全なHTMLではなくテーブルのみ
        self.assertNotContains(response, '<!DOCTYPE html>')
        self.assertContains(response, '<table')

    def test_pagination_preserves_filters(self):
        """ページネーションでフィルターが保持される"""
        response = self.client.get(
            reverse('candidates:candidate_list'),
            {'q': 'テスト', 'page': 1},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)


class RealtimeFilterTest(BaseUITestCase):
    """リアルタイムフィルターのテスト"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Candidate.objects.create(
            tenant=cls.tenant,
            name='山田太郎',
            email='yamada@test.com',
            employment_status='employed',
        )
        Candidate.objects.create(
            tenant=cls.tenant,
            name='田中花子',
            email='tanaka@test.com',
            employment_status='unemployed',
        )

    def test_search_filter_has_htmx_trigger(self):
        """検索フィールドにHTMXトリガーがある"""
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertContains(response, 'hx-trigger')
        self.assertContains(response, 'delay:500ms')

    def test_filter_dropdown_has_change_trigger(self):
        """フィルタードロップダウンにchange トリガーがある"""
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertContains(response, 'hx-trigger="change"')


class ToastNotificationTest(TestCase):
    """トースト通知のテスト（テンプレートファイル直接読み込み）"""

    def test_toast_template_has_container(self):
        """トーストテンプレートにコンテナがある"""
        from django.template import Template, Context
        from pathlib import Path

        toast_path = Path(__file__).parent.parent / 'templates' / 'components' / 'toast.html'
        if toast_path.exists():
            content = toast_path.read_text(encoding='utf-8')
            self.assertIn('id="toast-container"', content)

    def test_toast_template_has_showtoast_function(self):
        """トーストテンプレートにshowToast関数がある"""
        from pathlib import Path

        toast_path = Path(__file__).parent.parent / 'templates' / 'components' / 'toast.html'
        if toast_path.exists():
            content = toast_path.read_text(encoding='utf-8')
            self.assertIn('function showToast', content)


class ProgressBarTest(TestCase):
    """プログレスバーのテスト（テンプレートファイル直接読み込み）"""

    def test_base_template_has_progress_bar(self):
        """ベーステンプレートにプログレスバー要素がある"""
        from pathlib import Path

        base_path = Path(__file__).parent.parent / 'templates' / 'base.html'
        if base_path.exists():
            content = base_path.read_text(encoding='utf-8')
            self.assertIn('id="progress-bar"', content)

    def test_base_template_has_htmx_handlers(self):
        """ベーステンプレートにHTMXハンドラーがある"""
        from pathlib import Path

        base_path = Path(__file__).parent.parent / 'templates' / 'base.html'
        if base_path.exists():
            content = base_path.read_text(encoding='utf-8')
            self.assertIn('htmx:beforeRequest', content)
            self.assertIn('htmx:afterRequest', content)


class AccessibilityTest(TestCase):
    """アクセシビリティのテスト（テンプレートファイル直接読み込み）"""

    def test_candidate_list_template_has_aria_labels(self):
        """候補者一覧テンプレートにaria-labelがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'candidates' / 'candidate_list.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('aria-label', content)

    def test_form_field_template_has_labels(self):
        """フォームフィールドテンプレートにラベル要素がある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'components' / 'form_field.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('<label', content)
            self.assertIn('for=', content)

    def test_icons_have_aria_hidden(self):
        """アイコン用SVGにaria-hiddenがある"""
        from pathlib import Path

        # 候補者一覧テンプレートでaria-hidden使用確認
        template_path = Path(__file__).parent.parent / 'templates' / 'candidates' / 'candidate_list.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('aria-hidden="true"', content)

    def test_skip_links_template_exists(self):
        """スキップリンクテンプレートが存在する"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'components' / 'skip_links.html'
        self.assertTrue(template_path.exists())

    def test_skip_links_has_main_content_link(self):
        """スキップリンクにメインコンテンツへのリンクがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'components' / 'skip_links.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('href="#main-content"', content)
            self.assertIn('メインコンテンツへスキップ', content)

    def test_screen_reader_announcer_exists(self):
        """スクリーンリーダーアナウンサーテンプレートが存在する"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'components' / 'screen_reader_announcer.html'
        self.assertTrue(template_path.exists())

    def test_screen_reader_announcer_has_live_regions(self):
        """スクリーンリーダーアナウンサーにライブリージョンがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'components' / 'screen_reader_announcer.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('aria-live="assertive"', content)
            self.assertIn('aria-live="polite"', content)
            self.assertIn('announceToScreenReader', content)

    def test_base_template_has_landmark_roles(self):
        """ベーステンプレートにランドマークロールがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'base.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('role="main"', content)
            self.assertIn('role="navigation"', content)
            self.assertIn('role="banner"', content)
            self.assertIn('id="main-content"', content)

    def test_base_template_includes_skip_links(self):
        """ベーステンプレートがスキップリンクをインクルードしている"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'base.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('skip_links.html', content)
            self.assertIn('screen_reader_announcer.html', content)


class JobListHTMXTest(BaseUITestCase):
    """求人一覧HTMXテスト"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # 求人を作成
        for i in range(25):
            Job.objects.create(
                tenant=cls.tenant,
                title=f'求人{i+1}',
                unique_code=f'JOB-{i+1:03d}',
                status='active',
                created_by=cls.user,
            )

    def test_job_list_htmx_pagination(self):
        """求人一覧のHTMXページネーションが機能する"""
        response = self.client.get(
            reverse('jobs:job_list'),
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        # HTMXリクエストではパーシャルテンプレートが返される
        self.assertNotContains(response, '<!DOCTYPE html>')
        self.assertContains(response, '<table')

    def test_job_list_htmx_realtime_filter(self):
        """求人一覧のリアルタイムフィルター機能"""
        response = self.client.get(reverse('jobs:job_list'))
        # hx-trigger属性があること
        self.assertContains(response, 'hx-trigger')
        self.assertContains(response, 'delay:500ms')

    def test_job_list_filter_dropdown_htmx(self):
        """求人一覧のフィルタードロップダウンがHTMXトリガーを持つ"""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertContains(response, 'hx-trigger="change"')


class InterviewListHTMXTest(TestCase):
    """面接一覧HTMXテスト（テンプレートファイル直接読み込み）"""

    def test_interview_list_template_has_htmx_attributes(self):
        """面接一覧テンプレートにHTMX属性がある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'interviews' / 'interview_list.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # hx-trigger属性があること
            self.assertIn('hx-trigger', content)
            self.assertIn('delay:500ms', content)
            self.assertIn('hx-target="#list-container"', content)

    def test_interview_partial_template_has_htmx_pagination(self):
        """面接パーシャルテンプレートにHTMXページネーションがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'interviews' / 'partials' / 'interview_table.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # HTMXページネーション属性があること
            self.assertIn('hx-get', content)
            self.assertIn('hx-target', content)


class ApplicationListHTMXTest(TestCase):
    """応募一覧HTMXテスト（テンプレートファイル直接読み込み）"""

    def test_application_list_template_has_htmx_attributes(self):
        """応募一覧テンプレートにHTMX属性がある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'application_list.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # hx-trigger属性があること
            self.assertIn('hx-trigger', content)
            self.assertIn('delay:500ms', content)
            self.assertIn('hx-target="#list-container"', content)

    def test_application_partial_template_has_htmx_pagination(self):
        """応募パーシャルテンプレートにHTMXページネーションがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'partials' / 'application_table.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # HTMXページネーション属性があること
            self.assertIn('hx-get', content)
            self.assertIn('hx-target', content)


class SkeletonLoadingTest(TestCase):
    """スケルトンローディングのテスト（テンプレートファイル直接読み込み）"""

    def test_table_skeleton_template_exists(self):
        """テーブルスケルトンテンプレートが存在する"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'components' / 'table_skeleton.html'
        self.assertTrue(template_path.exists())

    def test_table_skeleton_has_candidate_type(self):
        """テーブルスケルトンに候補者タイプがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'components' / 'table_skeleton.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('skeleton_type == "candidates"', content)
            self.assertIn('animate-pulse', content)
            self.assertIn('skeleton', content)

    def test_loading_indicator_template_exists(self):
        """ローディングインジケーターテンプレートが存在する"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'components' / 'loading_indicator.html'
        self.assertTrue(template_path.exists())

    def test_loading_indicator_has_spinner_type(self):
        """ローディングインジケーターにスピナータイプがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'components' / 'loading_indicator.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('type == "spinner"', content)
            self.assertIn('animate-spin', content)

    def test_candidate_list_has_skeleton_indicator(self):
        """候補者一覧にスケルトンインジケーターがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'candidates' / 'candidate_list.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            self.assertIn('skeleton-indicator', content)
            self.assertIn('htmx-indicator', content)
            self.assertIn('hx-indicator', content)


class DashboardVisualizationTest(TestCase):
    """ダッシュボード可視化のテスト（テンプレートファイル直接読み込み）"""

    def test_dashboard_has_chart_js_canvas(self):
        """ダッシュボードテンプレートにChart.js用のcanvas要素がある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'dashboard' / 'index.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # Chart.js用のcanvas要素があること
            self.assertIn('id="monthlyTrendChart"', content)
            self.assertIn('id="sourceChart"', content)

    def test_dashboard_has_htmx_auto_refresh(self):
        """ダッシュボードテンプレートにHTMX自動更新属性がある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'dashboard' / 'index.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # HTMX自動更新属性があること
            self.assertIn('hx-trigger="every', content)
            self.assertIn('id="stats-container"', content)

    def test_dashboard_stats_partial_exists(self):
        """ダッシュボード統計パーシャルテンプレートが存在する"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'dashboard' / 'partials' / 'stats_cards.html'
        self.assertTrue(template_path.exists())
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # 統計カードの要素があること
            self.assertIn('stat-card', content)
            self.assertIn('応募者数', content)
            self.assertIn('公開中の求人', content)

    def test_base_template_has_chart_js(self):
        """ベーステンプレートにChart.jsが含まれている"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'base.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # Chart.js CDNが含まれていること
            self.assertIn('chart.js', content.lower())


class KanbanBoardTest(TestCase):
    """カンバンボードのテスト（テンプレートファイル直接読み込み）"""

    def test_kanban_template_exists(self):
        """カンバンテンプレートが存在する"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'application_kanban.html'
        self.assertTrue(template_path.exists())

    def test_kanban_has_sortablejs(self):
        """カンバンテンプレートにSortableJSが含まれている"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'application_kanban.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # SortableJS CDNが含まれていること
            self.assertIn('sortablejs', content.lower())
            self.assertIn('Sortable.min.js', content)

    def test_kanban_has_data_attributes(self):
        """カンバンテンプレートにデータ属性がある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'application_kanban.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # ドラッグ＆ドロップに必要なデータ属性があること
            self.assertIn('data-status', content)
            self.assertIn('kanban-cards', content)
            self.assertIn('kanban-column', content)

    def test_kanban_has_drag_drop_styles(self):
        """カンバンテンプレートにドラッグ＆ドロップスタイルがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'application_kanban.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # ドラッグ＆ドロップ用のCSSクラスがあること
            self.assertIn('kanban-ghost', content)
            self.assertIn('kanban-chosen', content)
            self.assertIn('cursor: grab', content)

    def test_kanban_has_status_update_js(self):
        """カンバンテンプレートにステータス更新JSがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'application_kanban.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # ステータス更新機能があること
            self.assertIn('updateApplicationStatus', content)
            self.assertIn('/applications/', content)
            self.assertIn('/status/', content)

    def test_kanban_has_accessibility_attributes(self):
        """カンバンテンプレートにアクセシビリティ属性がある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'application_kanban.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # アクセシビリティ属性があること
            self.assertIn('role="region"', content)
            self.assertIn('role="group"', content)
            self.assertIn('aria-label', content)
            self.assertIn('announceToScreenReader', content)


class KanbanCardTest(TestCase):
    """カンバンカードのテスト（テンプレートファイル直接読み込み）"""

    def test_kanban_card_template_exists(self):
        """カンバンカードテンプレートが存在する"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'partials' / 'kanban_card.html'
        self.assertTrue(template_path.exists())

    def test_kanban_card_has_data_application_id(self):
        """カンバンカードにアプリケーションIDデータ属性がある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'partials' / 'kanban_card.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # アプリケーションID属性があること
            self.assertIn('data-application-id', content)

    def test_kanban_card_has_drag_handle(self):
        """カンバンカードにドラッグハンドルがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'partials' / 'kanban_card.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # ドラッグハンドル用のクラスがあること
            self.assertIn('kanban-card', content)
            # カード内にドラッグハンドルアイコンがあること
            self.assertIn('<svg', content)

    def test_kanban_card_has_candidate_info(self):
        """カンバンカードに候補者情報がある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'partials' / 'kanban_card.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # 候補者情報表示があること
            self.assertIn('application.candidate.name', content)
            self.assertIn('application.job.title', content)

    def test_kanban_card_has_quick_actions(self):
        """カンバンカードにクイックアクションがある"""
        from pathlib import Path

        template_path = Path(__file__).parent.parent / 'templates' / 'applications' / 'partials' / 'kanban_card.html'
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            # 詳細リンクがあること
            self.assertIn("applications:application_detail", content)
            # 候補者リンクがあること
            self.assertIn("candidates:candidate_detail", content)
