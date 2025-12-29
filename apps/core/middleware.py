"""
Django ATS - ミドルウェア
テナント分離とその他のカスタムミドルウェア
"""

import logging
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone

logger = logging.getLogger(__name__)


class TenantMiddleware:
    """
    テナント分離ミドルウェア

    機能:
    - 認証済みユーザーのテナントをリクエストに設定
    - テナントの有効期限チェック
    - システム管理者の特別処理
    """

    # テナントチェックを除外するパス
    EXEMPT_PATHS = [
        '/admin/',
        '/accounts/',
        '/static/',
        '/media/',
        '/__debug__/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # デフォルト値設定
        request.tenant = None
        request.tenant_id = None
        request.is_system_admin = False

        # 除外パスのチェック
        if self._is_exempt_path(request.path):
            return self.get_response(request)

        if request.user.is_authenticated:
            # システム管理者チェック
            if hasattr(request.user, 'role') and request.user.role == 'system_admin':
                request.is_system_admin = True
                # システム管理者はテナントなしでもアクセス可能
                self._set_tenant_from_session_or_user(request)
            else:
                # 通常ユーザーはテナント必須
                if not self._set_tenant_from_user(request):
                    # テナントがない場合はダッシュボードにリダイレクト
                    if request.path != '/dashboard/' and not request.path.startswith('/accounts/'):
                        messages.warning(request, 'テナントが設定されていません。')
                        return redirect('core:dashboard')

                # テナントの有効期限チェック
                if not self._check_tenant_validity(request):
                    messages.error(request, 'テナントの有効期限が切れています。')
                    return redirect('accounts:logout')

        response = self.get_response(request)
        return response

    def _is_exempt_path(self, path):
        """除外パスかどうかをチェック"""
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)

    def _set_tenant_from_user(self, request):
        """ユーザーからテナントを設定"""
        if hasattr(request.user, 'tenant') and request.user.tenant:
            request.tenant = request.user.tenant
            request.tenant_id = request.user.tenant_id
            return True
        return False

    def _set_tenant_from_session_or_user(self, request):
        """セッションまたはユーザーからテナントを設定（システム管理者用）"""
        # セッションからテナントIDを取得
        session_tenant_id = request.session.get('selected_tenant_id')
        if session_tenant_id:
            try:
                from apps.tenants.models import Tenant
                tenant = Tenant.objects.get(id=session_tenant_id, is_active=True)
                request.tenant = tenant
                request.tenant_id = tenant.id
                return True
            except Tenant.DoesNotExist:
                pass

        # ユーザーのテナントを使用
        return self._set_tenant_from_user(request)

    def _check_tenant_validity(self, request):
        """テナントの有効性をチェック"""
        if not request.tenant:
            return True  # テナントがない場合はチェック不要

        # アクティブフラグチェック
        if not request.tenant.is_active:
            logger.warning(f"Inactive tenant access attempt: {request.tenant.id}")
            return False

        # 有効期限チェック
        if hasattr(request.tenant, 'expires_at') and request.tenant.expires_at:
            if timezone.now() > request.tenant.expires_at:
                logger.warning(f"Expired tenant access attempt: {request.tenant.id}")
                return False

        return True


class AuditLogMiddleware:
    """
    監査ログミドルウェア

    重要な操作をデータベースとログファイルに記録。
    POST/PUT/PATCH/DELETEリクエストを自動的に記録。
    """

    # ログ対象のメソッド
    LOG_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

    # ログ除外パス
    EXEMPT_PATHS = [
        '/static/',
        '/media/',
        '/__debug__/',
        '/health/',
        '/favicon.ico',
    ]

    # パスからリソースタイプへのマッピング
    PATH_TO_RESOURCE = {
        '/candidates/': 'Candidate',
        '/jobs/': 'Job',
        '/applications/': 'Application',
        '/interviews/': 'Interview',
        '/accounts/': 'User',
        '/settings/': 'Settings',
        '/reports/': 'Report',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # レスポンス後にログを記録（成功した操作のみDB保存）
        if self._should_log(request):
            self._log_operation(request, response)

        return response

    def _should_log(self, request):
        """ログ対象かどうかをチェック"""
        if request.method not in self.LOG_METHODS:
            return False
        if any(request.path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return False
        return True

    def _get_resource_type(self, path):
        """パスからリソースタイプを判定"""
        for prefix, resource_type in self.PATH_TO_RESOURCE.items():
            if prefix in path:
                return resource_type
        return 'Unknown'

    def _get_action(self, method, path):
        """HTTPメソッドとパスからアクションを判定"""
        if method == 'DELETE':
            return 'delete'
        if method == 'POST':
            if 'create' in path or path.endswith('/'):
                return 'create'
            if 'import' in path:
                return 'import'
            if 'export' in path:
                return 'export'
            return 'create'
        if method in ['PUT', 'PATCH']:
            return 'update'
        return 'other'

    def _log_operation(self, request, response):
        """操作をログに記録"""
        from .models import AuditLog, AuditActionChoices

        user = request.user if request.user.is_authenticated else None
        tenant = getattr(request, 'tenant', None)
        resource_type = self._get_resource_type(request.path)
        action = self._get_action(request.method, request.path)

        # ログファイルに記録（エラーレスポンスはwarningレベル）
        user_str = user.email if user else 'anonymous'
        tenant_str = tenant.name if tenant else 'none'
        log_message = (
            f"[AUDIT] {request.method} {request.path} "
            f"status={response.status_code} user={user_str} tenant={tenant_str}"
        )
        if response.status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # 成功した操作のみデータベースに記録
        if response.status_code < 400:
            try:
                AuditLog.log(
                    action=action,
                    resource_type=resource_type,
                    request=request,
                    user=user,
                    tenant=tenant,
                    status_code=response.status_code,
                )
            except Exception as e:
                logger.error(f"[AUDIT] Failed to save audit log: {e}")
