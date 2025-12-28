"""Django ATS - アカウントフォーム完全カバレッジテスト

accounts/forms.pyの100%カバレッジを目指すテスト。
"""

import pytest
from django.core.exceptions import ValidationError

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRole
from apps.accounts.forms import UserCreateForm, PasswordResetForm


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='アカウントフォームテスト',
        code='account-form-test',
        is_active=True,
    )


# =============================================================================
# UserCreateForm Tests
# =============================================================================

class TestUserCreateFormSave:
    """UserCreateForm.saveメソッドテスト"""

    @pytest.mark.django_db
    def test_save_creates_user_with_tenant(self, tenant):
        """テナント付きでユーザーを作成"""
        form_data = {
            'email': 'newuser@form-test.com',
            'first_name': '太郎',
            'last_name': '山田',
            'role': UserRole.CLIENT_RECRUITER,
            'is_active': True,
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        }

        form = UserCreateForm(data=form_data, tenant=tenant)

        assert form.is_valid(), form.errors

        user = form.save()

        assert user.email == 'newuser@form-test.com'
        assert user.first_name == '太郎'
        assert user.last_name == '山田'
        assert user.tenant == tenant
        assert user.check_password('SecurePass123!')

    @pytest.mark.django_db
    def test_save_creates_user_without_tenant(self):
        """テナントなしでユーザーを作成"""
        form_data = {
            'email': 'notenant@form-test.com',
            'first_name': '次郎',
            'last_name': '鈴木',
            'role': UserRole.SYSTEM_ADMIN,
            'is_active': True,
            'password1': 'SecurePass456!',
            'password2': 'SecurePass456!',
        }

        form = UserCreateForm(data=form_data, tenant=None)

        assert form.is_valid(), form.errors

        user = form.save()

        assert user.email == 'notenant@form-test.com'
        assert user.tenant is None

    @pytest.mark.django_db
    def test_save_with_commit_false(self, tenant):
        """commit=Falseでユーザーを作成"""
        form_data = {
            'email': 'nocommit@form-test.com',
            'first_name': '三郎',
            'last_name': '田中',
            'role': UserRole.CLIENT_ADMIN,
            'is_active': True,
            'password1': 'SecurePass789!',
            'password2': 'SecurePass789!',
        }

        form = UserCreateForm(data=form_data, tenant=tenant)

        assert form.is_valid(), form.errors

        user = form.save(commit=False)

        # UUID主キーは保存前でも生成されるが、DBには保存されていない
        assert user.pk is not None  # UUIDは事前生成される
        assert user.tenant == tenant
        assert user.check_password('SecurePass789!')
        # DBにはまだ保存されていないことを確認
        assert not CustomUser.objects.filter(email='nocommit@form-test.com').exists()


# =============================================================================
# PasswordResetForm Tests
# =============================================================================

class TestPasswordResetFormClean:
    """PasswordResetForm.clean_new_password2メソッドテスト"""

    def test_clean_password_match(self):
        """パスワードが一致する場合"""
        form_data = {
            'new_password1': 'MatchingPass123!',
            'new_password2': 'MatchingPass123!',
        }

        form = PasswordResetForm(data=form_data)

        assert form.is_valid()
        assert form.cleaned_data['new_password2'] == 'MatchingPass123!'

    def test_clean_password_mismatch(self):
        """パスワードが一致しない場合"""
        form_data = {
            'new_password1': 'Password123!',
            'new_password2': 'DifferentPass456!',
        }

        form = PasswordResetForm(data=form_data)

        assert form.is_valid() is False
        assert 'new_password2' in form.errors
        assert 'パスワードが一致しません' in form.errors['new_password2'][0]

    def test_clean_password_empty_password1(self):
        """password1が空の場合"""
        form_data = {
            'new_password1': '',
            'new_password2': 'SomePass123!',
        }

        form = PasswordResetForm(data=form_data)

        # password1が必須なのでエラー
        assert form.is_valid() is False
        assert 'new_password1' in form.errors
