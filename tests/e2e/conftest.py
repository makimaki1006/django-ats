"""
E2Eテスト用pytest設定
"""

import os
import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """ブラウザコンテキストの設定"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "ja-JP",
    }


@pytest.fixture(scope="function")
def page(browser):
    """各テスト用のページ"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="ja-JP",
    )
    page = context.new_page()
    yield page
    page.close()
    context.close()
