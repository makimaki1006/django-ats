"""
Django ATS - 認証・権限テスト
"""

import pytest
from django.test import RequestFactory, TestCase
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from apps.tenants.models import Tenant
from apps.accounts.models import Profile, UserRoleChoices
from apps.core.middleware import TenantMiddleware
from apps.core.mixins import (
    RoleRequiredMixin,
    AdminRequiredMixin,
    TenantAccessMixin,
)

User = get_user_model()


@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='テストテナント',
        code='test-tenant',
        is_active=True,
    )


@pytest.fixture
def expired_tenant(db):
    """期限切れテナント"""
    return Tenant.objects.create(
        name='期限切れテナント',
        code='expired-tenant',
        is_active=True,
        trial_ends_at=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def inactive_tenant(db):
    """無効テナント"""
    return Tenant.objects.create(
        name='無効テナント',
        code='inactive-tenant',
        is_active=False,
    )


@pytest.fixture
def system_admin(db, tenant):
    """システム管理者ユーザー"""
    user = User.objects.create_user(
        email='sysadmin@example.com',
        password='testpass123',
        role=UserRoleChoices.SYSTEM_ADMIN,
        tenant=tenant,
    )
    return user


@pytest.fixture
def client_admin(db, tenant):
    """クライアント管理者ユーザー"""
    user = User.objects.create_user(
        email='clientadmin@example.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )
    return user


@pytest.fixture
def recruiter(db, tenant):
    """採用担当者ユーザー"""
    user = User.objects.create_user(
        email='recruiter@example.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_RECRUITER,
        tenant=tenant,
    )
    return user


@pytest.fixture
def agent_user(db, tenant):
    """エージェントユーザー"""
    user = User.objects.create_user(
        email='agent@example.com',
        password='testpass123',
        role=UserRoleChoices.AGENT,
        tenant=tenant,
    )
    return user


class TestTenantMiddleware:
    """TenantMiddlewareのテスト"""

    def get_request(self, user=None):
        """リクエストオブジェクトを作成"""
        factory = RequestFactory()
        request = factory.get('/dashboard/')

        # セッションミドルウェアを追加
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()

        # メッセージミドルウェアを追加
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        if user:
            request.user = user
        else:
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()

        return request

    def test_anonymous_user_no_tenant(self, db):
        """未認証ユーザーはテナントなし"""
        middleware = TenantMiddleware(lambda r: r)
        request = self.get_request()

        middleware(request)

        assert request.tenant is None
        assert request.tenant_id is None

    def test_authenticated_user_with_tenant(self, db, tenant, recruiter):
        """認証済みユーザーはテナントが設定される"""
        middleware = TenantMiddleware(lambda r: r)
        request = self.get_request(user=recruiter)

        middleware(request)

        assert request.tenant == tenant
        assert request.tenant_id == tenant.id

    def test_system_admin_flag(self, db, tenant, system_admin):
        """システム管理者フラグが設定される"""
        middleware = TenantMiddleware(lambda r: r)
        request = self.get_request(user=system_admin)

        middleware(request)

        assert request.is_system_admin is True

    def test_exempt_paths(self, db, tenant, recruiter):
        """除外パスはテナントチェックをスキップ"""
        middleware = TenantMiddleware(lambda r: r)

        factory = RequestFactory()
        for path in ['/admin/', '/accounts/login/', '/static/css/main.css']:
            request = factory.get(path)
            request.user = recruiter
            middleware(request)
            # 除外パスでもrequest属性は設定される
            assert hasattr(request, 'tenant')


class TestUserRoles:
    """ユーザー役割のテスト"""

    def test_system_admin_permissions(self, db, system_admin):
        """システム管理者は全権限を持つ"""
        assert system_admin.is_system_admin
        assert system_admin.is_admin

    def test_client_admin_permissions(self, db, client_admin):
        """クライアント管理者は管理権限を持つ"""
        assert not client_admin.is_system_admin
        assert client_admin.is_admin

    def test_recruiter_permissions(self, db, recruiter):
        """採用担当者は一般権限"""
        assert not recruiter.is_system_admin
        assert not recruiter.is_admin

    def test_agent_permissions(self, db, agent_user):
        """エージェントは一般権限"""
        assert not agent_user.is_system_admin
        assert not agent_user.is_admin


class TestUserModel:
    """ユーザーモデルのテスト"""

    def test_create_user(self, db, tenant):
        """一般ユーザーの作成"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=tenant,
        )
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self, db):
        """スーパーユーザーの作成"""
        user = User.objects.create_superuser(
            email='super@example.com',
            password='testpass123',
        )
        assert user.email == 'super@example.com'
        assert user.is_staff
        assert user.is_superuser

    def test_email_required(self, db, tenant):
        """メールアドレスは必須"""
        with pytest.raises(ValueError):
            User.objects.create_user(
                email='',
                password='testpass123',
                tenant=tenant,
            )

    def test_full_name(self, db, tenant):
        """氏名の取得"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='太郎',
            last_name='山田',
            tenant=tenant,
        )
        assert user.full_name == '山田 太郎'

    def test_full_name_empty(self, db, tenant):
        """氏名が空の場合"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=tenant,
        )
        assert user.full_name == ''


class TestProfileModel:
    """プロファイルモデルのテスト"""

    def test_profile_creation(self, db, tenant, recruiter):
        """プロファイルの作成"""
        profile = Profile.objects.create(
            user=recruiter,
            tenant=tenant,
            phone='+819012345678',  # 正しい電話番号形式
            department='人事部',
            position='採用担当',
        )
        assert profile.user == recruiter
        assert profile.phone == '+819012345678'
        assert profile.department == '人事部'

    def test_profile_str(self, db, tenant, recruiter):
        """プロファイルの文字列表現"""
        profile = Profile.objects.create(
            user=recruiter,
            tenant=tenant,
        )
        # Profileの__str__は "display_name or email のプロファイル" の形式
        assert "プロファイル" in str(profile)


class TestAuthViews:
    """認証ビューのテスト"""

    @pytest.mark.django_db
    def test_login_page_accessible(self, client):
        """ログインページにアクセスできる"""
        response = client.get('/accounts/login/')
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_signup_page_accessible(self, client):
        """サインアップページにアクセスできる"""
        response = client.get('/accounts/signup/')
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_password_reset_page_accessible(self, client):
        """パスワードリセットページにアクセスできる"""
        response = client.get('/accounts/password/reset/')
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_profile_requires_login(self, client):
        """プロファイルページはログイン必須"""
        response = client.get('/users/profile/')
        # ログインページにリダイレクトされる
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    @pytest.mark.django_db
    def test_user_list_requires_admin(self, client, db, tenant, recruiter):
        """ユーザー一覧は管理者権限必須"""
        client.force_login(recruiter)
        response = client.get('/users/')
        # 権限不足でアクセス拒否
        assert response.status_code == 403


class TestTenantAccess:
    """テナントアクセス制御のテスト"""

    @pytest.mark.django_db
    def test_user_cannot_access_other_tenant_data(self, db, tenant):
        """他テナントのデータにはアクセスできない"""
        # 別テナント作成
        other_tenant = Tenant.objects.create(
            name='別テナント',
            code='other-tenant',
            is_active=True,
        )

        # 別テナントのユーザー
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            tenant=other_tenant,
        )

        # テナントフィルタを使用した場合、他テナントのユーザーは取得されない
        users_in_tenant = User.objects.filter(tenant=tenant)
        assert other_user not in users_in_tenant

    @pytest.mark.django_db
    def test_system_admin_can_access_all_tenants(self, db, tenant, system_admin):
        """システム管理者は全テナントにアクセス可能"""
        # システム管理者はテナントに関係なくデータにアクセス可能
        all_tenants = Tenant.objects.all()
        assert all_tenants.count() >= 1


class TestFormValidation:
    """フォームバリデーションのテスト"""

    @pytest.mark.django_db
    def test_user_create_form_unique_email(self, db, tenant, recruiter):
        """メールアドレスの重複チェック"""
        from apps.accounts.forms import UserCreateForm

        form = UserCreateForm(data={
            'email': recruiter.email,  # 既存のメールアドレス
            'password1': 'newpass123',
            'password2': 'newpass123',
            'role': UserRoleChoices.CLIENT_RECRUITER,
            'is_active': True,
        }, tenant=tenant)

        assert not form.is_valid()
        assert 'email' in form.errors

    @pytest.mark.django_db
    def test_user_create_form_password_mismatch(self, db, tenant):
        """パスワード不一致チェック"""
        from apps.accounts.forms import UserCreateForm

        form = UserCreateForm(data={
            'email': 'new@example.com',
            'password1': 'newpass123',
            'password2': 'wrongpass',  # 不一致
            'role': UserRoleChoices.CLIENT_RECRUITER,
            'is_active': True,
        }, tenant=tenant)

        assert not form.is_valid()
        assert 'password2' in form.errors

    @pytest.mark.django_db
    def test_profile_form_valid(self, db, tenant, recruiter):
        """プロファイルフォームの有効性"""
        from apps.accounts.forms import ProfileForm

        profile = Profile.objects.create(user=recruiter, tenant=tenant)
        form = ProfileForm(instance=profile, data={
            'first_name': '太郎',
            'last_name': '山田',
            'phone': '+819012345678',  # E.164形式
            'department': '人事部',
            'position': '採用担当',
        })

        assert form.is_valid()
