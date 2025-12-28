"""Django ATS - pytest設定 & 共通Fixtures

全テストで使用するfixture、factory、設定を定義。
"""

import os
import pytest
import uuid
from django.test import RequestFactory
from django.contrib.auth import get_user_model


# E2Eテスト（Playwright）でDjango非同期コンテキスト問題を回避
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


# Django設定を読み込む
pytest_plugins = ['pytest_django']


@pytest.fixture
def request_factory():
    """Django RequestFactory"""
    return RequestFactory()


@pytest.fixture
def mock_request(request_factory):
    """モックリクエスト（テナント情報付き）"""
    request = request_factory.get('/')
    request.tenant = None
    request.tenant_id = None
    return request


@pytest.fixture
def sample_uuid():
    """サンプルUUID"""
    return uuid.uuid4()
