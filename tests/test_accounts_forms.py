"""Django ATS - アカウントフォームテスト

アカウント関連フォームのテスト。
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.forms import ProfileForm, UserCreateForm, UserUpdateForm
from apps.accounts.models import CustomUser, Profile, UserRoleChoices
from apps.tenants.models import Tenant


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='フォームテスト',
        code='form-test',
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """テストユーザー"""
    return CustomUser.objects.create_user(
        email='user@form-test.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


# =============================================================================
# ProfileForm Tests
# =============================================================================

class TestProfileForm:
    """ProfileForm のテスト"""

    @pytest.mark.django_db
    def test_profile_form_valid(self, tenant, user):
        """有効なプロファイルフォーム"""
        profile = Profile.objects.create(user=user, tenant=tenant)
        form = ProfileForm(
            data={
                'phone': '09012345678',
                'department': '開発部',
                'position': 'エンジニア',
                'first_name': '太郎',
                'last_name': '山田',
            },
            instance=profile,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_profile_form_empty(self, tenant, user):
        """空のプロファイルフォームは有効"""
        profile = Profile.objects.create(user=user, tenant=tenant)
        form = ProfileForm(data={
            'first_name': '',
            'last_name': '',
        }, instance=profile)
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_profile_form_fields(self, tenant, user):
        """フォームフィールドが正しい"""
        profile = Profile.objects.create(user=user, tenant=tenant)
        form = ProfileForm(instance=profile)
        # フォームにフィールドがあることを確認
        assert 'phone' in form.fields
        assert 'department' in form.fields
        assert 'first_name' in form.fields


# =============================================================================
# UserCreateForm Tests
# =============================================================================

class TestUserCreateForm:
    """UserCreateForm のテスト"""

    @pytest.mark.django_db
    def test_user_create_form_valid(self, tenant):
        """有効なユーザー作成フォーム"""
        form = UserCreateForm(
            data={
                'email': 'newuser@form-test.com',
                'password1': 'testpass123!',
                'password2': 'testpass123!',
                'role': UserRoleChoices.CLIENT_ADMIN,  # テナント内で許可されるロール
                'is_active': True,
            },
            tenant=tenant,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_user_create_form_without_tenant(self):
        """テナントなしのユーザー作成フォーム"""
        form = UserCreateForm(
            data={
                'email': 'newuser2@form-test.com',
                'password1': 'testpass123!',
                'password2': 'testpass123!',
                'role': UserRoleChoices.INTERVIEWER,
                'is_active': True,
            },
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_user_create_form_password_mismatch(self, tenant):
        """パスワード不一致でエラー"""
        form = UserCreateForm(
            data={
                'email': 'newuser@form-test.com',
                'password1': 'testpass123!',
                'password2': 'differentpass!',
                'role': UserRoleChoices.CLIENT_ADMIN,
                'is_active': True,
            },
            tenant=tenant,
        )
        assert not form.is_valid()

    @pytest.mark.django_db
    def test_user_create_form_duplicate_email(self, tenant, user):
        """重複メールでエラー"""
        form = UserCreateForm(
            data={
                'email': 'user@form-test.com',  # 既存のメール
                'password1': 'testpass123!',
                'password2': 'testpass123!',
                'role': UserRoleChoices.CLIENT_ADMIN,
                'is_active': True,
            },
            tenant=tenant,
        )
        assert not form.is_valid()
        assert 'email' in form.errors


# =============================================================================
# UserUpdateForm Tests
# =============================================================================

class TestUserUpdateForm:
    """UserUpdateForm のテスト"""

    @pytest.mark.django_db
    def test_user_update_form_valid(self, user):
        """有効なユーザー更新フォーム"""
        form = UserUpdateForm(
            data={
                'email': 'updated@form-test.com',
                'role': UserRoleChoices.CLIENT_ADMIN,
                'is_active': True,
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_user_update_form_change_role(self, user):
        """ロール変更"""
        form = UserUpdateForm(
            data={
                'email': user.email,
                'role': UserRoleChoices.HIRING_MANAGER,
                'is_active': True,
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_user_update_form_deactivate(self, user):
        """ユーザー無効化"""
        form = UserUpdateForm(
            data={
                'email': user.email,
                'role': user.role,
                'is_active': False,
            },
            instance=user,
        )
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_user_update_form_duplicate_email(self, tenant, user):
        """重複メールでエラー"""
        # 別ユーザーを作成
        other_user = CustomUser.objects.create_user(
            email='other@form-test.com',
            password='testpass123',
            role=UserRoleChoices.INTERVIEWER,
            tenant=tenant,
        )
        # 既存のメールアドレスに変更しようとする
        form = UserUpdateForm(
            data={
                'email': 'other@form-test.com',  # 他のユーザーのメール
                'role': user.role,
                'is_active': True,
            },
            instance=user,
        )
        assert not form.is_valid()
        assert 'email' in form.errors
