"""
Django ATS - アカウント関連フォーム
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError

from .models import CustomUser, Profile, UserRoleChoices


class CustomUserCreationForm(UserCreationForm):
    """カスタムユーザー作成フォーム（管理画面用）"""

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'role')


class CustomUserChangeForm(UserChangeForm):
    """カスタムユーザー変更フォーム（管理画面用）"""

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'role', 'is_active')


class ProfileForm(forms.ModelForm):
    """プロファイル更新フォーム"""

    # ユーザー情報も同時に編集可能にする
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label='名前',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '太郎',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='姓',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '山田',
        })
    )

    class Meta:
        model = Profile
        fields = ['phone', 'department', 'position', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '090-1234-5678',
            }),
            'department': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '人事部',
            }),
            'position': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '採用担当',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 既存のユーザー情報をセット
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        # ユーザー情報も更新
        if profile.user:
            profile.user.first_name = self.cleaned_data.get('first_name', '')
            profile.user.last_name = self.cleaned_data.get('last_name', '')
            if commit:
                profile.user.save()
        if commit:
            profile.save()
        return profile


class UserCreateForm(forms.ModelForm):
    """ユーザー作成フォーム（管理者用）"""

    password1 = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'autocomplete': 'new-password',
        }),
        help_text='8文字以上で設定してください。',
    )
    password2 = forms.CharField(
        label='パスワード（確認）',
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'autocomplete': 'new-password',
        }),
    )

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'role', 'is_active']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'user@example.com',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'role': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

        # システム管理者はテナント管理者以外は作成不可
        # （テナント内で作成できるロールを制限）
        if tenant:
            self.fields['role'].choices = [
                (UserRoleChoices.CLIENT_ADMIN, 'クライアント管理者'),
                (UserRoleChoices.CLIENT_RECRUITER, '採用担当者'),
                (UserRoleChoices.AGENT, 'エージェント'),
            ]

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('パスワードが一致しません。')
        return password2

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('このメールアドレスは既に使用されています。')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if self.tenant:
            user.tenant = self.tenant
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    """ユーザー更新フォーム（管理者用）"""

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'role', 'is_active']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'role': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # 自分自身以外で同じメールアドレスがないかチェック
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise ValidationError('このメールアドレスは既に使用されています。')
        return email


class PasswordResetForm(forms.Form):
    """パスワードリセットフォーム（管理者用）"""

    new_password1 = forms.CharField(
        label='新しいパスワード',
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'autocomplete': 'new-password',
        }),
        help_text='8文字以上で設定してください。',
    )
    new_password2 = forms.CharField(
        label='新しいパスワード（確認）',
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'autocomplete': 'new-password',
        }),
    )

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('パスワードが一致しません。')
        return password2
