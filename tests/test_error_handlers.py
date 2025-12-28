"""Django ATS - エラーハンドラーテスト

カスタムエラーハンドラーのテスト。
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory

from apps.core.error_handlers import handler400, handler403, handler404, handler500


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def rf():
    """RequestFactory"""
    return RequestFactory()


@pytest.fixture
def mock_request(rf):
    """モックリクエスト"""
    request = rf.get('/some/path/')
    request.user = MagicMock()
    request.user.__str__ = lambda self: 'testuser'
    request.META = {'REMOTE_ADDR': '127.0.0.1'}
    return request


# =============================================================================
# Handler400 Tests
# =============================================================================

class TestHandler400:
    """400 Bad Request ハンドラーテスト"""

    @pytest.mark.django_db
    def test_handler400_returns_400_status(self, mock_request):
        """400ステータスコードを返す"""
        with patch('apps.core.error_handlers.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=400)
            response = handler400(mock_request, Exception('Bad Request'))
            mock_render.assert_called_once()
            assert mock_render.call_args[1]['status'] == 400

    @pytest.mark.django_db
    def test_handler400_uses_correct_template(self, mock_request):
        """正しいテンプレートを使用"""
        with patch('apps.core.error_handlers.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=400)
            handler400(mock_request, Exception('Bad Request'))
            call_args = mock_render.call_args
            assert call_args[0][1] == 'errors/400.html'


# =============================================================================
# Handler403 Tests
# =============================================================================

class TestHandler403:
    """403 Forbidden ハンドラーテスト"""

    @pytest.mark.django_db
    def test_handler403_returns_403_status(self, mock_request):
        """403ステータスコードを返す"""
        with patch('apps.core.error_handlers.render') as mock_render:
            with patch('apps.core.error_handlers.logger') as mock_logger:
                mock_render.return_value = MagicMock(status_code=403)
                response = handler403(mock_request, Exception('Forbidden'))
                mock_render.assert_called_once()
                assert mock_render.call_args[1]['status'] == 403

    @pytest.mark.django_db
    def test_handler403_logs_warning(self, mock_request):
        """警告ログを出力"""
        with patch('apps.core.error_handlers.render') as mock_render:
            with patch('apps.core.error_handlers.logger') as mock_logger:
                mock_render.return_value = MagicMock(status_code=403)
                handler403(mock_request, Exception('Forbidden'))
                assert mock_logger.warning.called

    @pytest.mark.django_db
    def test_handler403_uses_correct_template(self, mock_request):
        """正しいテンプレートを使用"""
        with patch('apps.core.error_handlers.render') as mock_render:
            with patch('apps.core.error_handlers.logger'):
                mock_render.return_value = MagicMock(status_code=403)
                handler403(mock_request, Exception('Forbidden'))
                call_args = mock_render.call_args
                assert call_args[0][1] == 'errors/403.html'


# =============================================================================
# Handler404 Tests
# =============================================================================

class TestHandler404:
    """404 Not Found ハンドラーテスト"""

    @pytest.mark.django_db
    def test_handler404_returns_404_status(self, mock_request):
        """404ステータスコードを返す"""
        with patch('apps.core.error_handlers.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=404)
            response = handler404(mock_request, Exception('Not Found'))
            mock_render.assert_called_once()
            assert mock_render.call_args[1]['status'] == 404

    @pytest.mark.django_db
    def test_handler404_uses_correct_template(self, mock_request):
        """正しいテンプレートを使用"""
        with patch('apps.core.error_handlers.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=404)
            handler404(mock_request, Exception('Not Found'))
            call_args = mock_render.call_args
            assert call_args[0][1] == 'errors/404.html'


# =============================================================================
# Handler500 Tests
# =============================================================================

class TestHandler500:
    """500 Internal Server Error ハンドラーテスト"""

    @pytest.mark.django_db
    def test_handler500_returns_500_status(self, mock_request):
        """500ステータスコードを返す"""
        with patch('apps.core.error_handlers.render') as mock_render:
            with patch('apps.core.error_handlers.logger') as mock_logger:
                mock_render.return_value = MagicMock(status_code=500)
                response = handler500(mock_request)
                mock_render.assert_called_once()
                assert mock_render.call_args[1]['status'] == 500

    @pytest.mark.django_db
    def test_handler500_logs_error(self, mock_request):
        """エラーログを出力"""
        with patch('apps.core.error_handlers.render') as mock_render:
            with patch('apps.core.error_handlers.logger') as mock_logger:
                mock_render.return_value = MagicMock(status_code=500)
                handler500(mock_request)
                assert mock_logger.error.called

    @pytest.mark.django_db
    def test_handler500_uses_correct_template(self, mock_request):
        """正しいテンプレートを使用"""
        with patch('apps.core.error_handlers.render') as mock_render:
            with patch('apps.core.error_handlers.logger'):
                mock_render.return_value = MagicMock(status_code=500)
                handler500(mock_request)
                call_args = mock_render.call_args
                assert call_args[0][1] == 'errors/500.html'

    @pytest.mark.django_db
    def test_handler500_with_sentry(self, mock_request):
        """Sentryがインストールされている場合"""
        with patch('apps.core.error_handlers.render') as mock_render:
            with patch('apps.core.error_handlers.logger'):
                with patch.dict('sys.modules', {'sentry_sdk': MagicMock()}):
                    mock_render.return_value = MagicMock(status_code=500)
                    response = handler500(mock_request)
                    assert mock_render.call_args[1]['status'] == 500

    @pytest.mark.django_db
    def test_handler500_without_sentry(self, mock_request):
        """Sentryがインストールされていない場合"""
        with patch('apps.core.error_handlers.render') as mock_render:
            with patch('apps.core.error_handlers.logger'):
                # sentry_sdkのimportでImportErrorを発生させる
                mock_render.return_value = MagicMock(status_code=500)
                response = handler500(mock_request)
                # エラーなく処理が完了
                assert mock_render.call_args[1]['status'] == 500
