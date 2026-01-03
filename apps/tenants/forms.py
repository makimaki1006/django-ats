"""Django ATS - Tenants フォーム

テナント管理用フォーム。
"""

from django import forms

from apps.tenants.models import Tenant, TenantSpreadsheet


class TenantForm(forms.ModelForm):
    """テナントフォーム"""

    class Meta:
        model = Tenant
        fields = [
            'name',
            'code',
            'logo_url',
            'is_active',
            'plan',
            'max_users',
            'trial_ends_at',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': '株式会社〇〇',
            }),
            'code': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': 'example-corp',
            }),
            'logo_url': forms.URLInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': 'https://example.com/logo.png',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded',
            }),
            'plan': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            }),
            'max_users': forms.NumberInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'min': '1',
            }),
            'trial_ends_at': forms.DateTimeInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'type': 'datetime-local',
            }),
        }

    def clean_code(self):
        """コードのバリデーション"""
        code = self.cleaned_data.get('code')
        if code:
            # 小文字に統一
            code = code.lower()
            # 既存チェック（編集時は自分自身を除外）
            qs = Tenant.objects.filter(code=code)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('このコードは既に使用されています。')
        return code

    def clean_max_users(self):
        """最大ユーザー数のバリデーション"""
        max_users = self.cleaned_data.get('max_users')
        if max_users is not None and max_users < 1:
            raise forms.ValidationError('最大ユーザー数は1以上である必要があります。')

        # 編集時: 現在のユーザー数より少なくできない
        if self.instance and self.instance.pk:
            current_users = self.instance.user_count()
            if max_users < current_users:
                raise forms.ValidationError(
                    f'現在{current_users}名のユーザーが登録されているため、'
                    f'{current_users}以上を指定してください。'
                )

        return max_users


class TenantSpreadsheetForm(forms.ModelForm):
    """テナントスプレッドシートフォーム"""

    class Meta:
        model = TenantSpreadsheet
        fields = [
            'spreadsheet_id',
            'spreadsheet_name',
            'is_active',
        ]
        widgets = {
            'spreadsheet_id': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms',
            }),
            'spreadsheet_name': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': '採用管理シート',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded',
            }),
        }

    def clean_spreadsheet_id(self):
        """スプレッドシートIDのバリデーション"""
        spreadsheet_id = self.cleaned_data.get('spreadsheet_id')
        if spreadsheet_id:
            # URLから取り出す場合
            if 'docs.google.com/spreadsheets' in spreadsheet_id:
                import re
                match = re.search(r'/d/([a-zA-Z0-9-_]+)', spreadsheet_id)
                if match:
                    spreadsheet_id = match.group(1)
        return spreadsheet_id


class TenantFilterForm(forms.Form):
    """テナントフィルターフォーム"""

    is_active = forms.ChoiceField(
        choices=[
            ('', 'すべて'),
            ('true', '有効のみ'),
            ('false', '無効のみ'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
        }),
    )

    plan = forms.ChoiceField(
        choices=[('', 'すべて')] + list(Tenant.PlanChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
        }),
    )
