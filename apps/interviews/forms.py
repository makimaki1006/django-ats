"""
Django ATS - 面接フォーム
"""

from django import forms

from .models import (
    Interview,
    InterviewTypeChoices,
    InterviewStatusChoices,
    InterviewResultChoices,
)


class InterviewForm(forms.ModelForm):
    """面接作成・更新フォーム"""

    class Meta:
        model = Interview
        fields = [
            'application', 'interview_type', 'interview_round',
            'scheduled_at', 'duration_minutes', 'location',
            'interviewer', 'additional_interviewers',
            'status', 'internal_notes'
        ]
        widgets = {
            'application': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'interview_type': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'interview_round': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'min': 1,
                'max': 10,
            }),
            'scheduled_at': forms.DateTimeInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'datetime-local',
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'min': 15,
                'step': 15,
            }),
            'location': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Zoom URL または 住所',
            }),
            'interviewer': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'additional_interviewers': forms.SelectMultiple(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'status': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'internal_notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 2,
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

        if tenant:
            from apps.applications.models import Application
            from apps.accounts.models import CustomUser

            # テナントに紐づく応募のみ表示（進行中のもの）
            self.fields['application'].queryset = Application.objects.filter(
                tenant=tenant
            ).select_related('candidate', 'job').order_by('-applied_at')

            # テナントに紐づくユーザーのみ表示（面接官）
            users = CustomUser.objects.filter(tenant=tenant, is_active=True)
            self.fields['interviewer'].queryset = users
            self.fields['additional_interviewers'].queryset = users


class InterviewFilterForm(forms.Form):
    """面接フィルタフォーム"""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': '候補者名、求人名で検索...',
        })
    )

    status = forms.ChoiceField(
        choices=[('', 'すべてのステータス')] + list(InterviewStatusChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )

    date_filter = forms.ChoiceField(
        choices=[
            ('', 'すべての日程'),
            ('today', '今日'),
            ('week', '今週'),
            ('upcoming', '予定のみ'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )


class InterviewResultForm(forms.Form):
    """面接結果入力フォーム"""

    result = forms.ChoiceField(
        choices=InterviewResultChoices.choices,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )

    evaluation_score = forms.ChoiceField(
        choices=[('', '---')] + [(str(i), f'{i}点') for i in range(1, 6)],
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )

    feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'rows': 3,
            'placeholder': '候補者へのフィードバック...',
        })
    )

    internal_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'rows': 2,
            'placeholder': '社内メモ...',
        })
    )
