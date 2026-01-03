"""
Django ATS E2Eテスト - ログイン機能
Playwrightを使用したブラウザ自動化テスト
"""

import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
django.setup()

from playwright.sync_api import sync_playwright, expect
import pytest


# テスト用設定
BASE_URL = os.environ.get('E2E_BASE_URL', 'http://localhost:8000')
TEST_EMAIL = 'admin@example.com'
TEST_PASSWORD = 'admin123'


class TestLogin:
    """ログイン機能のE2Eテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, page):
        """テスト前のセットアップ"""
        self.page = page
        self.base_url = BASE_URL

    def test_login_page_accessible(self, page):
        """ログインページにアクセスできる"""
        page.goto(f'{BASE_URL}/accounts/login/')
        expect(page).to_have_title_containing('ログイン')

    def test_login_form_exists(self, page):
        """ログインフォームが存在する"""
        page.goto(f'{BASE_URL}/accounts/login/')
        expect(page.locator('input[name="login"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_login_with_invalid_credentials(self, page):
        """無効な認証情報でログイン失敗"""
        page.goto(f'{BASE_URL}/accounts/login/')
        page.fill('input[name="login"]', 'invalid@example.com')
        page.fill('input[name="password"]', 'wrongpassword')
        page.click('button[type="submit"]')

        # エラーメッセージが表示される
        expect(page.locator('.alert-danger, .errorlist')).to_be_visible()

    def test_login_with_valid_credentials(self, page):
        """有効な認証情報でログイン成功"""
        page.goto(f'{BASE_URL}/accounts/login/')
        page.fill('input[name="login"]', TEST_EMAIL)
        page.fill('input[name="password"]', TEST_PASSWORD)
        page.click('button[type="submit"]')

        # ダッシュボードにリダイレクト
        page.wait_for_url(f'{BASE_URL}/dashboard/')
        expect(page).to_have_url_containing('dashboard')


class TestDashboard:
    """ダッシュボードのE2Eテスト"""

    @pytest.fixture(autouse=True)
    def login(self, page):
        """テスト前にログイン"""
        page.goto(f'{BASE_URL}/accounts/login/')
        page.fill('input[name="login"]', TEST_EMAIL)
        page.fill('input[name="password"]', TEST_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url(f'{BASE_URL}/dashboard/')

    def test_dashboard_accessible(self, page):
        """ダッシュボードにアクセスできる"""
        expect(page).to_have_url_containing('dashboard')

    def test_dashboard_has_navigation(self, page):
        """ナビゲーションメニューが存在する"""
        expect(page.locator('nav, .sidebar, .navigation')).to_be_visible()

    def test_dashboard_has_stats(self, page):
        """統計情報が表示される"""
        # 統計カードまたはKPIが表示される
        expect(page.locator('.stat-card, .kpi, .card')).to_be_visible()


class TestCandidateList:
    """候補者一覧のE2Eテスト"""

    @pytest.fixture(autouse=True)
    def login(self, page):
        """テスト前にログイン"""
        page.goto(f'{BASE_URL}/accounts/login/')
        page.fill('input[name="login"]', TEST_EMAIL)
        page.fill('input[name="password"]', TEST_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url(f'{BASE_URL}/dashboard/')

    def test_candidate_list_accessible(self, page):
        """候補者一覧にアクセスできる"""
        page.goto(f'{BASE_URL}/candidates/')
        expect(page).to_have_url_containing('candidates')

    def test_candidate_list_has_table(self, page):
        """候補者テーブルが表示される"""
        page.goto(f'{BASE_URL}/candidates/')
        expect(page.locator('table, .candidate-list')).to_be_visible()

    def test_candidate_search_works(self, page):
        """候補者検索が機能する"""
        page.goto(f'{BASE_URL}/candidates/')
        search_input = page.locator('input[name="q"], input[type="search"]')
        if search_input.is_visible():
            search_input.fill('テスト')
            page.keyboard.press('Enter')
            # ページが更新される
            expect(page).to_have_url_containing('q=')


class TestJobList:
    """求人一覧のE2Eテスト"""

    @pytest.fixture(autouse=True)
    def login(self, page):
        """テスト前にログイン"""
        page.goto(f'{BASE_URL}/accounts/login/')
        page.fill('input[name="login"]', TEST_EMAIL)
        page.fill('input[name="password"]', TEST_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url(f'{BASE_URL}/dashboard/')

    def test_job_list_accessible(self, page):
        """求人一覧にアクセスできる"""
        page.goto(f'{BASE_URL}/jobs/')
        expect(page).to_have_url_containing('jobs')

    def test_job_list_has_content(self, page):
        """求人コンテンツが表示される"""
        page.goto(f'{BASE_URL}/jobs/')
        expect(page.locator('table, .job-list, .card')).to_be_visible()


class TestSettings:
    """設定画面のE2Eテスト"""

    @pytest.fixture(autouse=True)
    def login(self, page):
        """テスト前にログイン"""
        page.goto(f'{BASE_URL}/accounts/login/')
        page.fill('input[name="login"]', TEST_EMAIL)
        page.fill('input[name="password"]', TEST_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url(f'{BASE_URL}/dashboard/')

    def test_settings_accessible(self, page):
        """設定画面にアクセスできる"""
        page.goto(f'{BASE_URL}/settings/')
        expect(page).to_have_url_containing('settings')

    def test_settings_has_tabs(self, page):
        """設定タブが表示される"""
        page.goto(f'{BASE_URL}/settings/')
        # タブまたはナビゲーションが存在
        expect(page.locator('.tab, .nav-tabs, .settings-nav')).to_be_visible()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
