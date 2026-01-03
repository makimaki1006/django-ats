"""Django ATS - アカウントシグナル

ログイン/ログアウトイベントを監視し、履歴を記録。
"""

import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from apps.core.models import AuditLog, AuditActionChoices

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """ユーザーログイン成功時の処理

    - LoginHistoryに記録
    - AuditLogにも記録
    """
    from .models import LoginHistory

    # LoginHistoryに記録
    LoginHistory.log_login(
        email=user.email,
        success=True,
        request=request,
        user=user,
    )

    # AuditLogにも記録
    try:
        AuditLog.objects.create(
            tenant=user.tenant,
            user=user,
            action=AuditActionChoices.LOGIN,
            resource_type='CustomUser',
            resource_id=str(user.id),
            resource_repr=user.email,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
        )
    except Exception as e:
        logger.error(f"Failed to create audit log for login: {e}")

    logger.info(f"User logged in: {user.email}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """ユーザーログアウト時の処理

    - AuditLogに記録
    """
    if user is None:
        return

    try:
        AuditLog.objects.create(
            tenant=user.tenant,
            user=user,
            action=AuditActionChoices.LOGOUT,
            resource_type='CustomUser',
            resource_id=str(user.id),
            resource_repr=user.email,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
        )
    except Exception as e:
        logger.error(f"Failed to create audit log for logout: {e}")

    logger.info(f"User logged out: {user.email}")


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """ユーザーログイン失敗時の処理

    - LoginHistoryに記録（セキュリティ監視用）
    - 連続失敗回数をチェック
    """
    from .models import LoginHistory

    email = credentials.get('email', credentials.get('username', 'unknown'))

    # LoginHistoryに記録
    LoginHistory.log_login(
        email=email,
        success=False,
        request=request,
        user=None,
        failure_reason='invalid_credentials',
    )

    # 連続失敗回数をチェック（アカウントロック検討用）
    recent_failures = LoginHistory.get_recent_failures(email, hours=1)
    if recent_failures >= 5:
        logger.warning(f"Multiple login failures for {email}: {recent_failures} attempts in the last hour")

    logger.info(f"Login failed for: {email}")


def _get_client_ip(request):
    """クライアントIPアドレスを取得"""
    if request is None:
        return None

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
