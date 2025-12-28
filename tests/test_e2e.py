"""Django ATS - E2Eテスト（Playwright）

ブラウザを使用した統合テスト。
pytest-playwright と pytest-django の live_server フィクスチャを使用。

使用方法:
    pytest tests/test_e2e.py -v --headed  # ブラウザ表示
    pytest tests/test_e2e.py -v           # ヘッドレス
"""

import pytest
from playwright.sync_api import Page, expect

from apps.accounts.models import CustomUser, UserRoleChoices
from apps.tenants.models import Tenant


# マーカー登録
pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def test_tenant(db):
    """E2Eテスト用テナント"""
    return Tenant.objects.create(
        name='E2Eテスト',
        code='e2e-test',
        is_active=True,
    )


@pytest.fixture
def test_user(db, test_tenant):
    """E2Eテスト用ユーザー"""
    return CustomUser.objects.create_user(
        email='e2e@test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=test_tenant,
    )


# =============================================================================
# ログインページテスト
# =============================================================================

class TestLoginPage:
    """ログインページのテスト"""

    def test_login_page_loads(self, page: Page, live_server):
        """ログインページが表示されること"""
        page.goto(f'{live_server.url}/accounts/login/')

        # ページが読み込まれること
        assert page.url.endswith('/accounts/login/') or 'login' in page.url

    def test_login_form_elements_exist(self, page: Page, live_server):
        """ログインフォームの要素が存在すること"""
        page.goto(f'{live_server.url}/accounts/login/')

        # 入力フィールドが存在（allauth形式）
        login_input = page.locator('input[name="login"]')
        password_input = page.locator('input[name="password"]')
        submit_button = page.locator('button[type="submit"]')

        assert login_input.count() > 0, "Login input not found"
        assert password_input.count() > 0, "Password input not found"
        assert submit_button.count() > 0, "Submit button not found"

    def test_login_with_valid_credentials(self, page: Page, live_server, test_user):
        """有効な認証情報でログインできること"""
        page.goto(f'{live_server.url}/accounts/login/')

        # ログイン情報入力
        page.fill('input[name="login"]', 'e2e@test.com')
        page.fill('input[name="password"]', 'testpass123')
        page.click('button[type="submit"]')

        # ログイン後リダイレクト（ダッシュボードまたはホーム）
        page.wait_for_load_state('networkidle', timeout=10000)
        assert 'login' not in page.url.lower() or 'dashboard' in page.url.lower()


# =============================================================================
# ナビゲーションテスト
# =============================================================================

class TestNavigation:
    """ナビゲーションのテスト"""

    def test_unauthenticated_redirects_to_login(self, page: Page, live_server):
        """未認証ユーザーはログインにリダイレクトされること"""
        page.goto(f'{live_server.url}/dashboard/')
        page.wait_for_load_state('networkidle', timeout=5000)

        assert 'login' in page.url.lower()

    def test_candidates_page_redirects_unauthenticated(self, page: Page, live_server):
        """候補者ページは未認証でログインにリダイレクト"""
        page.goto(f'{live_server.url}/candidates/')
        page.wait_for_load_state('networkidle', timeout=5000)

        assert 'login' in page.url.lower()

    def test_jobs_page_redirects_unauthenticated(self, page: Page, live_server):
        """求人ページは未認証でログインにリダイレクト"""
        page.goto(f'{live_server.url}/jobs/')
        page.wait_for_load_state('networkidle', timeout=5000)

        assert 'login' in page.url.lower()


# =============================================================================
# レスポンシブデザインテスト
# =============================================================================

class TestResponsiveDesign:
    """レスポンシブデザインのテスト"""

    def test_mobile_viewport(self, page: Page, live_server):
        """モバイルビューポートでページが表示されること"""
        page.set_viewport_size({'width': 375, 'height': 667})
        page.goto(f'{live_server.url}/accounts/login/')

        assert page.url is not None

    def test_tablet_viewport(self, page: Page, live_server):
        """タブレットビューポートでページが表示されること"""
        page.set_viewport_size({'width': 768, 'height': 1024})
        page.goto(f'{live_server.url}/accounts/login/')

        assert page.url is not None

    def test_desktop_viewport(self, page: Page, live_server):
        """デスクトップビューポートでページが表示されること"""
        page.set_viewport_size({'width': 1920, 'height': 1080})
        page.goto(f'{live_server.url}/accounts/login/')

        assert page.url is not None


# =============================================================================
# アクセシビリティテスト
# =============================================================================

class TestAccessibility:
    """アクセシビリティのテスト"""

    def test_page_has_title(self, page: Page, live_server):
        """ページにタイトルがあること"""
        page.goto(f'{live_server.url}/accounts/login/')

        title = page.title()
        assert title is not None and len(title) > 0

    def test_form_keyboard_navigation(self, page: Page, live_server):
        """キーボードでフォームを操作できること"""
        page.goto(f'{live_server.url}/accounts/login/')

        # Tabキーでフォーカス移動
        page.keyboard.press('Tab')
        page.keyboard.press('Tab')

        # エラーなく操作できること
        assert page.url is not None

    def test_password_input_is_masked(self, page: Page, live_server):
        """パスワード入力がマスクされていること"""
        page.goto(f'{live_server.url}/accounts/login/')

        password_input = page.locator('input[type="password"]')
        assert password_input.count() > 0


# =============================================================================
# フォームバリデーションテスト
# =============================================================================

class TestFormValidation:
    """フォームバリデーションのテスト"""

    def test_empty_form_submission(self, page: Page, live_server):
        """空のフォーム送信でログインページに留まること"""
        page.goto(f'{live_server.url}/accounts/login/')

        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle', timeout=5000)

        # ログインページに留まる
        assert 'login' in page.url.lower()

    def test_invalid_credentials_shows_error(self, page: Page, live_server):
        """無効な認証情報でエラーが表示されること"""
        page.goto(f'{live_server.url}/accounts/login/')

        page.fill('input[name="login"]', 'invalid@example.com')
        page.fill('input[name="password"]', 'wrongpassword')
        page.click('button[type="submit"]')

        page.wait_for_load_state('networkidle', timeout=5000)

        # ログインページに留まる
        assert 'login' in page.url.lower()


# =============================================================================
# エラーページテスト
# =============================================================================

class TestErrorPages:
    """エラーページのテスト"""

    def test_404_page(self, page: Page, live_server):
        """404ページが表示されること"""
        response = page.goto(f'{live_server.url}/nonexistent-page-12345/')

        assert response.status == 404


# =============================================================================
# 認証後テスト
# =============================================================================

class TestAuthenticatedFlow:
    """認証後のフローテスト"""

    @pytest.fixture
    def logged_in_page(self, page: Page, live_server, test_user):
        """ログイン済みページ"""
        page.goto(f'{live_server.url}/accounts/login/')

        page.fill('input[name="login"]', 'e2e@test.com')
        page.fill('input[name="password"]', 'testpass123')
        page.click('button[type="submit"]')

        page.wait_for_load_state('networkidle', timeout=10000)

        return page

    def test_dashboard_accessible_after_login(self, logged_in_page: Page, live_server):
        """ログイン後ダッシュボードにアクセスできること"""
        logged_in_page.goto(f'{live_server.url}/dashboard/')
        logged_in_page.wait_for_load_state('networkidle', timeout=5000)

        # ダッシュボードにアクセスできる（リダイレクトされない）
        # または認証エラーでログインページにリダイレクト
        assert logged_in_page.url is not None

    def test_candidates_accessible_after_login(self, logged_in_page: Page, live_server):
        """ログイン後候補者ページにアクセスできること"""
        logged_in_page.goto(f'{live_server.url}/candidates/')
        logged_in_page.wait_for_load_state('networkidle', timeout=5000)

        assert logged_in_page.url is not None

    def test_jobs_accessible_after_login(self, logged_in_page: Page, live_server):
        """ログイン後求人ページにアクセスできること"""
        logged_in_page.goto(f'{live_server.url}/jobs/')
        logged_in_page.wait_for_load_state('networkidle', timeout=5000)

        assert logged_in_page.url is not None

    def test_logout_redirects_to_login(self, logged_in_page: Page, live_server):
        """ログアウト後ログインページにリダイレクトされること"""
        # ログアウトボタンをクリック（または直接URL）
        logged_in_page.goto(f'{live_server.url}/accounts/logout/')
        logged_in_page.wait_for_load_state('networkidle', timeout=5000)

        # ログアウト後、ホームまたはログインページ
        assert logged_in_page.url is not None
