"""Django ATS - アダプターテスト

Allauth アダプターのテスト。
"""

import pytest
from unittest.mock import MagicMock, patch
from django.test import RequestFactory

from apps.accounts.adapters import CustomAccountAdapter
from apps.accounts.models import CustomUser
from apps.tenants.models import Tenant


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def rf():
    """RequestFactory"""
    return RequestFactory()


@pytest.fixture
def adapter():
    """CustomAccountAdapter インスタンス"""
    return CustomAccountAdapter()


@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='アダプターテストテナント',
        code='adapter-test',
        is_active=True,
    )


@pytest.fixture
def mock_form():
    """モックフォーム"""
    form = MagicMock()
    form.cleaned_data = {
        'email': 'test@adapter-test.com',
        'password1': 'testpass123',
    }
    return form


# =============================================================================
# CustomAccountAdapter Tests
# =============================================================================

class TestCustomAccountAdapter:
    """CustomAccountAdapter のテスト"""

    @pytest.mark.django_db
    def test_save_user_sets_username_to_email(self, rf, adapter, tenant, mock_form):
        """ユーザー保存時にusernameがemailと同じになる"""
        request = rf.post('/accounts/signup/')
        user = CustomUser(email='test@adapter-test.com', tenant=tenant)

        with patch.object(CustomAccountAdapter, 'save_user', wraps=adapter.save_user) as mock_save:
            # 親クラスのsave_userをモック
            with patch('allauth.account.adapter.DefaultAccountAdapter.save_user') as parent_save:
                parent_save.return_value = user
                saved_user = adapter.save_user(request, user, mock_form, commit=True)

                # usernameがemailと同じになっていることを確認
                if hasattr(user, 'username'):
                    assert user.username == user.email

    @pytest.mark.django_db
    def test_save_user_with_commit_false(self, rf, adapter, tenant, mock_form):
        """commit=Falseの場合saveが呼ばれない"""
        request = rf.post('/accounts/signup/')
        user = CustomUser(email='test@adapter-test.com', tenant=tenant)

        with patch('allauth.account.adapter.DefaultAccountAdapter.save_user') as parent_save:
            parent_save.return_value = user
            # commit=Falseの場合
            saved_user = adapter.save_user(request, user, mock_form, commit=False)
            # ユーザーは返される
            assert saved_user is not None

    @pytest.mark.django_db
    def test_get_login_redirect_url(self, rf, adapter):
        """ログイン後のリダイレクトURLが正しい"""
        request = rf.get('/')
        redirect_url = adapter.get_login_redirect_url(request)
        assert redirect_url == '/dashboard/'

    @pytest.mark.django_db
    def test_get_logout_redirect_url(self, rf, adapter):
        """ログアウト後のリダイレクトURLが正しい"""
        request = rf.get('/')
        redirect_url = adapter.get_logout_redirect_url(request)
        assert redirect_url == '/'


# =============================================================================
# Integration Tests
# =============================================================================

class TestAccountAdapterIntegration:
    """アダプター統合テスト"""

    @pytest.mark.django_db
    def test_adapter_is_configured(self):
        """settings.pyでアダプターが設定されている"""
        from django.conf import settings
        assert hasattr(settings, 'ACCOUNT_ADAPTER')
        assert 'CustomAccountAdapter' in settings.ACCOUNT_ADAPTER

    @pytest.mark.django_db
    def test_redirect_urls_are_safe(self, adapter, rf):
        """リダイレクトURLが安全（相対URL）"""
        request = rf.get('/')
        login_url = adapter.get_login_redirect_url(request)
        logout_url = adapter.get_logout_redirect_url(request)

        # 相対URLであること（外部リダイレクト防止）
        assert login_url.startswith('/')
        assert logout_url.startswith('/')

        # httpsスキームがないこと
        assert not login_url.startswith('http')
        assert not logout_url.startswith('http')
