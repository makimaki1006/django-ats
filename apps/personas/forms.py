"""
Django ATS - ペルソナフォーム
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Persona


class PersonaForm(forms.ModelForm):
    """ペルソナ作成・更新フォーム"""

    # JSONFieldをテキストエリアとして表示
    required_skills_text = forms.CharField(
        required=False,
        label='必須スキル',
        help_text='1行に1つのスキルを入力',
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            'rows': 3,
            'placeholder': 'Python\nDjango\nPostgreSQL',
        })
    )

    preferred_skills_text = forms.CharField(
        required=False,
        label='歓迎スキル',
        help_text='1行に1つのスキルを入力',
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            'rows': 3,
            'placeholder': 'AWS\nDocker\nKubernetes',
        })
    )

    personality_traits_text = forms.CharField(
        required=False,
        label='人物像・性格',
        help_text='1行に1つの特性を入力',
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            'rows': 3,
            'placeholder': 'コミュニケーション能力が高い\n主体的に行動できる\nチームワークを重視する',
        })
    )

    class Meta:
        model = Persona
        fields = [
            'name', 'description', 'is_template', 'is_active',
            'age_min', 'age_max', 'experience_years_min', 'experience_years_max',
            'education_level', 'work_style', 'motivation', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'placeholder': '例: 中堅エンジニア',
            }),
            'description': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'rows': 3,
                'placeholder': 'このペルソナの詳細な説明...',
            }),
            'is_template': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500',
            }),
            'age_min': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'min': 18,
                'max': 100,
                'placeholder': '25',
            }),
            'age_max': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'min': 18,
                'max': 100,
                'placeholder': '35',
            }),
            'experience_years_min': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'min': 0,
                'max': 50,
                'placeholder': '3',
            }),
            'experience_years_max': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'min': 0,
                'max': 50,
                'placeholder': '10',
            }),
            'education_level': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            }),
            'work_style': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'rows': 2,
                'placeholder': '例: リモートワーク可、フレックス勤務希望',
            }),
            'motivation': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'rows': 2,
                'placeholder': '例: 技術的成長を重視、新しい挑戦を求める',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
                'rows': 3,
                'placeholder': '補足情報...',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

        # 既存データがある場合、JSONFieldをテキストに変換
        if self.instance.pk:
            if self.instance.required_skills:
                self.fields['required_skills_text'].initial = '\n'.join(
                    self.instance.required_skills
                )
            if self.instance.preferred_skills:
                self.fields['preferred_skills_text'].initial = '\n'.join(
                    self.instance.preferred_skills
                )
            if self.instance.personality_traits:
                self.fields['personality_traits_text'].initial = '\n'.join(
                    self.instance.personality_traits
                )

    def clean(self):
        cleaned_data = super().clean()

        # 年齢の範囲チェック
        age_min = cleaned_data.get('age_min')
        age_max = cleaned_data.get('age_max')
        if age_min and age_max and age_min > age_max:
            raise ValidationError({
                'age_max': '最大年齢は最小年齢以上にしてください。'
            })

        # 経験年数の範囲チェック
        exp_min = cleaned_data.get('experience_years_min')
        exp_max = cleaned_data.get('experience_years_max')
        if exp_min and exp_max and exp_min > exp_max:
            raise ValidationError({
                'experience_years_max': '最大経験年数は最小経験年数以上にしてください。'
            })

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # テキストエリアからJSONFieldに変換
        required_skills_text = self.cleaned_data.get('required_skills_text', '')
        instance.required_skills = [
            s.strip() for s in required_skills_text.split('\n') if s.strip()
        ]

        preferred_skills_text = self.cleaned_data.get('preferred_skills_text', '')
        instance.preferred_skills = [
            s.strip() for s in preferred_skills_text.split('\n') if s.strip()
        ]

        personality_traits_text = self.cleaned_data.get('personality_traits_text', '')
        instance.personality_traits = [
            s.strip() for s in personality_traits_text.split('\n') if s.strip()
        ]

        if commit:
            instance.save()
        return instance


class PersonaFilterForm(forms.Form):
    """ペルソナフィルタフォーム"""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            'placeholder': 'ペルソナ名で検索...',
        })
    )

    is_active = forms.ChoiceField(
        choices=[('', 'すべて'), ('true', '有効のみ'), ('false', '無効のみ')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
        })
    )

    is_template = forms.ChoiceField(
        choices=[('', 'すべて'), ('true', 'テンプレートのみ'), ('false', '通常のみ')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
        })
    )

    education_level = forms.ChoiceField(
        choices=[('', 'すべての学歴')] + list(Persona.EducationLevelChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
        })
    )
