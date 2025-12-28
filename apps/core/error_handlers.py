"""
Django ATS - エラーハンドラー
カスタムエラーページの表示
"""

import logging

from django.shortcuts import render

logger = logging.getLogger(__name__)


def handler400(request, exception):
    """400 Bad Request"""
    return render(request, 'errors/400.html', status=400)


def handler403(request, exception):
    """403 Forbidden"""
    logger.warning(
        f"403 Forbidden: {request.path} by user={request.user} "
        f"IP={request.META.get('REMOTE_ADDR')}"
    )
    return render(request, 'errors/403.html', status=403)


def handler404(request, exception):
    """404 Not Found"""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """500 Internal Server Error"""
    try:
        import sentry_sdk
        sentry_sdk.capture_exception()
    except ImportError:
        pass

    logger.error(f"500 Error: {request.path}")
    return render(request, 'errors/500.html', status=500)
