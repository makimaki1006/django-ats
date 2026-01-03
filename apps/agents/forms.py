"""
Django ATS - エージェントフォーム
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import AgentCompany


class AgentCompanyForm(forms.ModelForm):
    """エージェント会社作成・更新フォーム"""

    class Meta:
        model = AgentCompany
        fields = [
            'name', 'code', 'contact_email', 'contact_phone', 'contact_person',
            'fee_rate', 'contract_start_date', 'contract_end_date',
            'is_active', 'is_preferred', 'address', 'website', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': '例: 株式会社○○人材',
            }),
            'code': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': '例: AGENT001',
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': 'contact@example.com',
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': '03-1234-5678',
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': '山田 太郎',
            }),
            'fee_rate': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'min': 0,
                'max': 100,
                'step': '0.01',
                'placeholder': '30.00',
            }),
            'contract_start_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'type': 'date',
            }),
            'contract_end_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'type': 'date',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500',
            }),
            'is_preferred': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500',
            }),
            'address': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'rows': 2,
                'placeholder': '東京都千代田区...',
            }),
            'website': forms.URLInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': 'https://www.example.com',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'rows': 3,
                'placeholder': '備考...',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            # 同一コードの重複チェック
            qs = AgentCompany.objects.filter(code=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('この会社コードは既に使用されています。')
        return code

    def clean(self):
        cleaned_data = super().clean()

        # 契約期間の整合性チェック
        start_date = cleaned_data.get('contract_start_date')
        end_date = cleaned_data.get('contract_end_date')
        if start_date and end_date and start_date > end_date:
            raise ValidationError({
                'contract_end_date': '契約終了日は開始日以降にしてください。'
            })

        return cleaned_data


class AgentCompanyFilterForm(forms.Form):
    """エージェント会社フィルタフォーム"""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            'placeholder': '会社名、コードで検索...',
        })
    )

    is_active = forms.ChoiceField(
        choices=[('', 'すべて'), ('true', '有効のみ'), ('false', '無効のみ')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
        })
    )

    is_preferred = forms.ChoiceField(
        choices=[('', 'すべて'), ('true', '優先パートナーのみ')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
        })
    )

    scope = forms.ChoiceField(
        choices=[('', 'すべて'), ('tenant', 'テナント固有'), ('global', 'グローバル')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
        })
    )
