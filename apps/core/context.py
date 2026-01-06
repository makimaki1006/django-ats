"""Django ATS - テナントコンテキスト管理

リクエストスコープでテナントを管理するためのモジュール。
ContextVarを使用して、スレッドセーフにテナント情報を保持。

使用方法:
    # ミドルウェアで設定
    set_current_tenant(request.user.tenant)

    # ビュー/サービスで取得
    tenant = get_current_tenant()

    # クエリセットの自動フィルタリング
    candidates = Candidate.objects.all()  # 自動的にテナントでフィルタ

Note:
    非同期処理（Celery等）では別途テナントを設定する必要がある。
"""

from contextvars import ContextVar
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.tenants.models import Tenant

# リクエストスコープのテナント
_current_tenant: ContextVar[Optional['Tenant']] = ContextVar(
    'current_tenant',
    default=None
)

# リクエストスコープのユーザー（オプション）
_current_user: ContextVar[Optional['CustomUser']] = ContextVar(
    'current_user',
    default=None
)


def get_current_tenant() -> Optional['Tenant']:
    """現在のテナントを取得

    Returns:
        Tenant or None: 現在のリクエストに紐づくテナント
    """
    return _current_tenant.get()


def set_current_tenant(tenant: Optional['Tenant']) -> None:
    """現在のテナントを設定

    Args:
        tenant: 設定するテナント（Noneでクリア）
    """
    _current_tenant.set(tenant)


def clear_current_tenant() -> None:
    """現在のテナントをクリア"""
    _current_tenant.set(None)


def get_current_user():
    """現在のユーザーを取得

    Returns:
        CustomUser or None: 現在のリクエストユーザー
    """
    return _current_user.get()


def set_current_user(user) -> None:
    """現在のユーザーを設定

    Args:
        user: 設定するユーザー（Noneでクリア）
    """
    _current_user.set(user)


def clear_current_user() -> None:
    """現在のユーザーをクリア"""
    _current_user.set(None)


class TenantContext:
    """テナントコンテキストマネージャー

    一時的にテナントを変更したい場合に使用。

    使用例:
        with TenantContext(other_tenant):
            # このブロック内ではother_tenantが現在のテナント
            candidates = Candidate.objects.all()

        # ブロック外では元のテナントに戻る
    """

    def __init__(self, tenant: Optional['Tenant']):
        self.tenant = tenant
        self.previous_tenant = None

    def __enter__(self):
        self.previous_tenant = get_current_tenant()
        set_current_tenant(self.tenant)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_current_tenant(self.previous_tenant)
        return False


def require_tenant(func):
    """テナント必須デコレータ

    テナントが設定されていない場合に例外を発生。

    使用例:
        @require_tenant
        def my_view(request):
            tenant = get_current_tenant()
            # tenantは必ず存在する
    """
    from functools import wraps
    from apps.core.exceptions import TenantNotSetError

    @wraps(func)
    def wrapper(*args, **kwargs):
        tenant = get_current_tenant()
        if tenant is None:
            raise TenantNotSetError("テナントが設定されていません")
        return func(*args, **kwargs)

    return wrapper
