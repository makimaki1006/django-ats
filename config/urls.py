"""
Django ATS URL Configuration
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    """ヘルスチェックエンドポイント（Render.com用）"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'django-ats',
    })


urlpatterns = [
    # ヘルスチェック（認証不要）
    path('health/', health_check, name='health_check'),

    path('admin/', admin.site.urls),

    # django-allauth
    path('accounts/', include('allauth.urls')),

    # アプリケーションURL
    path('', include('apps.core.urls')),
    path('dashboard/', include('apps.core.urls_dashboard')),
    path('candidates/', include('apps.candidates.urls')),
    path('applications/', include('apps.applications.urls')),
    path('jobs/', include('apps.jobs.urls')),
    path('interviews/', include('apps.interviews.urls')),
    path('personas/', include('apps.personas.urls')),
    path('agents/', include('apps.agents.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('reports/', include('apps.reports.urls')),
    path('settings/', include('apps.settings_app.urls')),
    path('tenants/', include('apps.tenants.urls')),
    path('users/', include('apps.accounts.urls')),
]

# エラーハンドラー
handler400 = 'apps.core.error_handlers.handler400'
handler403 = 'apps.core.error_handlers.handler403'
handler404 = 'apps.core.error_handlers.handler404'
handler500 = 'apps.core.error_handlers.handler500'

# 開発環境用設定
if settings.DEBUG:
    # メディアファイルの配信
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # django-debug-toolbar（オプション）
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
