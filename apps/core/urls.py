"""
Django ATS - Core URLs
"""

from django.urls import path
from django.views.generic import RedirectView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View


class GlobalSearchView(LoginRequiredMixin, TemplateView):
    """グローバル検索（スタブ）"""
    template_name = 'core/search.html'


class HealthCheckView(View):
    """ヘルスチェックエンドポイント"""

    def get(self, request):
        """システムの稼働状態を返す"""
        from django.db import connection
        from django.core.cache import cache

        health = {
            'status': 'healthy',
            'database': 'ok',
            'cache': 'ok',
        }

        # データベース接続チェック
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception:
            health['database'] = 'error'
            health['status'] = 'unhealthy'

        # キャッシュ接続チェック
        try:
            cache.set('health_check', 'ok', 1)
            if cache.get('health_check') != 'ok':
                health['cache'] = 'error'
        except Exception:
            health['cache'] = 'unavailable'

        status_code = 200 if health['status'] == 'healthy' else 503
        return JsonResponse(health, status=status_code)


app_name = 'core'

urlpatterns = [
    # ルートURLはダッシュボードにリダイレクト
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='index'),
    # グローバル検索
    path('search/', GlobalSearchView.as_view(), name='search'),
    # ヘルスチェック
    path('health/', HealthCheckView.as_view(), name='health'),
]
