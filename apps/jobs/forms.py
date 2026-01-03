"""
Django ATS - 求人フォーム
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Job, JobStatusChoices, EmploymentTypeChoices
from apps.personas.models import Persona
from apps.agents.models import AgentCompany


class JobForm(forms.ModelForm):
    """求人作成・更新フォーム"""

    # ペルソナ選択フィールド
    personas = forms.ModelMultipleChoiceField(
        queryset=Persona.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox',
        }),
        label='ペルソナ',
        help_text='この求人に紐付けるペルソナを選択してください'
    )

    # エージェント選択フィールド
    agent_companies = forms.ModelMultipleChoiceField(
        queryset=AgentCompany.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox',
        }),
        label='依頼エージェント',
        help_text='この求人を依頼するエージェント会社を選択してください'
    )

    class Meta:
        model = Job
        fields = [
            'title', 'unique_code', 'status',
            'department', 'team', 'hiring_manager',
            'employment_type', 'location', 'remote_policy',
            'salary_min', 'salary_max', 'salary_notes',
            'description', 'requirements', 'preferred_requirements',
            'benefits', 'selection_process',
            'headcount', 'deadline', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'ソフトウェアエンジニア',
            }),
            'unique_code': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'JOB-2025-001',
            }),
            'status': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'department': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '開発部',
            }),
            'team': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'バックエンドチーム',
            }),
            'hiring_manager': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'employment_type': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'location': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '東京都渋谷区',
            }),
            'remote_policy': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'フルリモート可',
            }),
            'salary_min': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '500',
                'min': 0,
            }),
            'salary_max': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '800',
                'min': 0,
            }),
            'salary_notes': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '経験・スキルに応じて決定',
            }),
            'description': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 5,
            }),
            'requirements': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 4,
            }),
            'preferred_requirements': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
            }),
            'benefits': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
            }),
            'selection_process': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 2,
                'placeholder': '書類選考 → 一次面接 → 二次面接 → 最終面接',
            }),
            'headcount': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'min': 1,
            }),
            'deadline': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 2,
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

        if tenant:
            # テナントに紐づくユーザーのみ表示（採用責任者）
            from apps.accounts.models import CustomUser
            self.fields['hiring_manager'].queryset = CustomUser.objects.filter(
                tenant=tenant, is_active=True
            )

            # ペルソナ: テナントに紐づくもののみ
            self.fields['personas'].queryset = Persona.objects.filter(
                tenant=tenant, is_active=True
            ).order_by('name')

            # エージェント: テナントに紐づくもの + グローバル
            from django.db.models import Q
            self.fields['agent_companies'].queryset = AgentCompany.objects.filter(
                Q(tenant=tenant) | Q(tenant__isnull=True),
                is_active=True
            ).order_by('name')

        # 編集時は既存の関連を初期値として設定
        if self.instance.pk:
            self.fields['personas'].initial = self.instance.personas.all()
            self.fields['agent_companies'].initial = self.instance.agent_companies.all()

    def clean_unique_code(self):
        unique_code = self.cleaned_data.get('unique_code')
        if unique_code and self.tenant:
            # 同一テナント内で求人コードの重複チェック
            qs = Job.objects.filter(tenant=self.tenant, unique_code=unique_code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('この求人コードは既に使用されています。')
        return unique_code

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')

        # 年収範囲の整合性チェック
        if salary_min and salary_max and salary_min > salary_max:
            raise ValidationError({
                'salary_max': '年収上限は下限以上の値を設定してください。'
            })

        return cleaned_data


class JobFilterForm(forms.Form):
    """求人フィルタフォーム"""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': 'タイトル、コードで検索...',
        })
    )

    status = forms.ChoiceField(
        choices=[('', 'すべてのステータス')] + list(JobStatusChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )

    employment_type = forms.ChoiceField(
        choices=[('', 'すべての雇用形態')] + list(EmploymentTypeChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )
