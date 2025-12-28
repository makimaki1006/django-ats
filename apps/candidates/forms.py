"""
Django ATS - 候補者フォーム
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Candidate, GenderChoices, EmploymentStatusChoices


class CandidateForm(forms.ModelForm):
    """候補者作成・更新フォーム"""

    class Meta:
        model = Candidate
        fields = [
            'name', 'name_kana', 'email', 'phone',
            'gender', 'birth_date', 'address',
            'current_company', 'current_position', 'employment_status',
            'years_of_experience', 'desired_salary',
            'education', 'can_relocate', 'available_from',
            'resume_url', 'cv_url', 'agent_company', 'source', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '山田 太郎',
            }),
            'name_kana': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'ヤマダ タロウ',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'example@email.com',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '+819012345678',
            }),
            'gender': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date',
            }),
            'address': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 2,
            }),
            'current_company': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'current_position': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'employment_status': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'min': 0,
                'max': 50,
            }),
            'desired_salary': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '500',
            }),
            'education': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '○○大学 ○○学部 卒業',
            }),
            'can_relocate': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'available_from': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date',
            }),
            'resume_url': forms.URLInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'cv_url': forms.URLInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'agent_company': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'source': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

        # テナントに紐づくエージェント会社のみ表示
        if tenant:
            from apps.agents.models import AgentCompany
            self.fields['agent_company'].queryset = AgentCompany.objects.filter(
                tenant=tenant, is_active=True
            )
            # 流入経路もテナントでフィルタ
            from apps.settings_app.models import ApplicationSource
            self.fields['source'].queryset = ApplicationSource.objects.filter(
                tenant=tenant, is_active=True
            )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.tenant:
            # 同一テナント内でメールアドレスの重複チェック
            qs = Candidate.objects.filter(tenant=self.tenant, email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('このメールアドレスは既に登録されています。')
        return email


class CandidateFilterForm(forms.Form):
    """候補者フィルタフォーム"""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': '氏名、メールで検索...',
        })
    )

    employment_status = forms.ChoiceField(
        choices=[('', 'すべての就業状況')] + list(EmploymentStatusChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )

    gender = forms.ChoiceField(
        choices=[('', 'すべての性別')] + list(GenderChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )

    agent_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500',
        })
    )

    include_archived = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500',
        })
    )


class CSVImportForm(forms.Form):
    """CSVインポートフォーム"""

    csv_file = forms.FileField(
        label='CSVファイル',
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
            'accept': '.csv',
        })
    )

    skip_duplicates = forms.BooleanField(
        required=False,
        initial=True,
        label='重複をスキップ',
        help_text='同じメールアドレスの候補者が既に存在する場合、スキップします',
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-500 focus:ring-blue-500',
        })
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            # ファイルサイズチェック（10MB以下）
            if csv_file.size > 10 * 1024 * 1024:
                raise ValidationError('ファイルサイズは10MB以下にしてください。')

            # 拡張子チェック
            if not csv_file.name.endswith('.csv'):
                raise ValidationError('CSVファイルのみアップロード可能です。')

        return csv_file


class CommentForm(forms.Form):
    """コメント投稿フォーム"""

    content = forms.CharField(
        label='コメント',
        widget=forms.Textarea(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'rows': 3,
            'placeholder': 'コメントを入力...',
        })
    )

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise ValidationError('コメントを入力してください。')
        if len(content) > 10000:
            raise ValidationError('コメントは10,000文字以内で入力してください。')
        return content
