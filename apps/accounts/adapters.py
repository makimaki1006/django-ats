"""
Django ATS - Allauth アダプター
カスタムユーザーモデル用のアダプター
"""

from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    カスタムアカウントアダプター

    メールアドレスのみで認証するためのアダプター。
    usernameフィールドは使用しない。
    """

    def save_user(self, request, user, form, commit=True):
        """ユーザーを保存"""
        user = super().save_user(request, user, form, commit=False)
        # usernameはemailと同じにする（usernameフィールドは無効化されているが念のため）
        if hasattr(user, 'username'):
            user.username = user.email
        if commit:
            user.save()
        return user

    def get_login_redirect_url(self, request):
        """ログイン後のリダイレクトURL"""
        return '/dashboard/'

    def get_logout_redirect_url(self, request):
        """ログアウト後のリダイレクトURL"""
        return '/'
