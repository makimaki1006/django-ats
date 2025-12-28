"""
Django ATS - 応募フォーム
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Application, ApplicationStatusChoices
from apps.candidates.models import Candidate, GenderChoices, EmploymentStatusChoices


class ApplicationForm(forms.ModelForm):
    """応募作成・更新フォーム"""

    class Meta:
        model = Application
        fields = [
            'candidate', 'job', 'status', 'source',
            'evaluation_score', 'evaluation_notes',
            'offer_salary', 'offer_deadline', 'offer_notes',
            'joined_at', 'notes'
        ]
        widgets = {
            'candidate': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'job': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'status': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'source': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            }),
            'evaluation_score': forms.Select(
                choices=[('', '---')] + [(i, f'{i}点') for i in range(1, 6)],
                attrs={
                    'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                }
            ),
            'evaluation_notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
            }),
            'offer_salary': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '500',
                'min': 0,
            }),
            'offer_deadline': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date',
            }),
            'offer_notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 2,
            }),
            'joined_at': forms.DateInput(attrs={
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
            from apps.candidates.models import Candidate
            from apps.jobs.models import Job
            from apps.settings_app.models import ApplicationSource

            # テナントに紐づく候補者のみ表示
            self.fields['candidate'].queryset = Candidate.objects.filter(
                tenant=tenant, is_archived=False
            ).order_by('name')

            # テナントに紐づく求人のみ表示（アクティブなもの優先）
            self.fields['job'].queryset = Job.objects.filter(
                tenant=tenant
            ).order_by('-status', 'title')

            # テナントに紐づく応募経路のみ表示
            self.fields['source'].queryset = ApplicationSource.objects.filter(
                tenant=tenant, is_active=True
            ).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        candidate = cleaned_data.get('candidate')
        job = cleaned_data.get('job')

        # 同じ候補者×求人の重複チェック
        if candidate and job:
            qs = Application.objects.filter(candidate=candidate, job=job)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    'この候補者は既にこの求人に応募しています。'
                )

        return cleaned_data


class ApplicationFilterForm(forms.Form):
    """応募フィルタフォーム"""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'placeholder': '候補者名、メール、求人名で検索...',
        })
    )

    status = forms.ChoiceField(
        choices=[('', 'すべてのステータス')] + list(ApplicationStatusChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )

    job = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label='すべての求人',
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )

    active_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500',
        })
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)

        if tenant:
            from apps.jobs.models import Job
            self.fields['job'].queryset = Job.objects.filter(
                tenant=tenant
            ).order_by('title')


class ApplicationStatusForm(forms.Form):
    """ステータス変更フォーム"""

    status = forms.ChoiceField(
        choices=ApplicationStatusChoices.choices,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
        })
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
            'rows': 2,
            'placeholder': '変更理由やメモを入力...',
        })
    )


class UnifiedApplicationForm(forms.Form):
    """統合応募フォーム

    外部ユーザー（コンサルタント、人材紹介会社、顧客）が
    候補者情報と応募情報を一度に入力するためのフォーム。

    設計ポイント:
    - 候補者の新規作成と応募の同時登録
    - 既存候補者の場合はメールで検出して選択可能
    - 流入チャネル（LINE/Email/Slack等）を統一
    """

    # ====================
    # 候補者基本情報
    # ====================
    name = forms.CharField(
        max_length=100,
        label='氏名',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '山田 太郎',
        })
    )

    name_kana = forms.CharField(
        max_length=100,
        required=False,
        label='氏名（カナ）',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'ヤマダ タロウ',
        })
    )

    email = forms.EmailField(
        label='メールアドレス',
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'example@email.com',
        })
    )

    phone = forms.CharField(
        max_length=17,
        required=False,
        label='電話番号',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '090-1234-5678',
        })
    )

    # ====================
    # 個人情報
    # ====================
    gender = forms.ChoiceField(
        choices=GenderChoices.choices,
        initial=GenderChoices.UNSPECIFIED,
        required=False,
        label='性別',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
        })
    )

    birth_date = forms.DateField(
        required=False,
        label='生年月日',
        widget=forms.DateInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'type': 'date',
        })
    )

    address = forms.CharField(
        required=False,
        label='住所',
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'rows': 2,
            'placeholder': '東京都渋谷区...',
        })
    )

    # ====================
    # 職歴情報
    # ====================
    current_company = forms.CharField(
        max_length=255,
        required=False,
        label='現職企業',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '株式会社〇〇',
        })
    )

    current_position = forms.CharField(
        max_length=255,
        required=False,
        label='現職役職',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '営業部 課長',
        })
    )

    employment_status = forms.ChoiceField(
        choices=EmploymentStatusChoices.choices,
        initial=EmploymentStatusChoices.EMPLOYED,
        required=False,
        label='就業状況',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
        })
    )

    years_of_experience = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=50,
        label='経験年数',
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '5',
        })
    )

    # ====================
    # 希望条件
    # ====================
    desired_salary = forms.IntegerField(
        required=False,
        min_value=0,
        label='希望年収（万円）',
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '500',
        })
    )

    available_from = forms.DateField(
        required=False,
        label='入社可能日',
        widget=forms.DateInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'type': 'date',
        })
    )

    # ====================
    # スキル・資格
    # ====================
    skills = forms.CharField(
        required=False,
        label='スキル',
        help_text='カンマ区切りで入力（例: Python, JavaScript, AWS）',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Python, JavaScript, AWS',
        })
    )

    qualifications = forms.CharField(
        required=False,
        label='資格',
        help_text='カンマ区切りで入力（例: 基本情報技術者, TOEIC 800点）',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '基本情報技術者, TOEIC 800点',
        })
    )

    education = forms.CharField(
        max_length=255,
        required=False,
        label='最終学歴',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': '〇〇大学 工学部卒',
        })
    )

    # ====================
    # 書類
    # ====================
    resume_url = forms.URLField(
        required=False,
        label='履歴書URL',
        widget=forms.URLInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'https://...',
        })
    )

    cv_url = forms.URLField(
        required=False,
        label='職務経歴書URL',
        widget=forms.URLInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'https://...',
        })
    )

    # ====================
    # 応募情報
    # ====================
    job = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label='応募求人',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
        })
    )

    source = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label='応募経路',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
        })
    )

    # ====================
    # 備考
    # ====================
    notes = forms.CharField(
        required=False,
        label='備考',
        widget=forms.Textarea(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'rows': 3,
            'placeholder': 'その他特記事項があれば入力してください',
        })
    )

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.user = user
        self._existing_candidate = None

        if tenant:
            from apps.jobs.models import Job
            from apps.settings_app.models import ApplicationSource

            # テナントに紐づく求人のみ表示（アクティブなもの）
            self.fields['job'].queryset = Job.objects.filter(
                tenant=tenant,
                status='active'
            ).order_by('title')

            # テナントに紐づく応募経路のみ表示
            self.fields['source'].queryset = ApplicationSource.objects.filter(
                tenant=tenant,
                is_active=True
            ).order_by('name')

    def clean_email(self):
        """メールアドレスの検証と既存候補者チェック"""
        email = self.cleaned_data['email']

        if self.tenant:
            # 既存候補者をチェック
            existing = Candidate.objects.filter(
                tenant=self.tenant,
                email=email
            ).first()

            if existing:
                self._existing_candidate = existing

        return email

    def clean(self):
        cleaned_data = super().clean()
        job = cleaned_data.get('job')

        # 既存候補者がいる場合、同じ求人への重複応募をチェック
        if self._existing_candidate and job:
            existing_application = Application.objects.filter(
                candidate=self._existing_candidate,
                job=job
            ).exists()

            if existing_application:
                raise ValidationError(
                    f'{self._existing_candidate.name}さんは既にこの求人に応募しています。'
                )

        return cleaned_data

    def save(self):
        """候補者と応募を保存

        Returns:
            tuple: (Candidate, Application, bool) - 候補者、応募、新規候補者かどうか
        """
        from apps.applications.models import Application, ApplicationStatusHistory

        # スキルと資格をリストに変換
        skills_str = self.cleaned_data.get('skills', '')
        skills = [s.strip() for s in skills_str.split(',') if s.strip()] if skills_str else []

        qualifications_str = self.cleaned_data.get('qualifications', '')
        qualifications = [q.strip() for q in qualifications_str.split(',') if q.strip()] if qualifications_str else []

        is_new_candidate = self._existing_candidate is None

        if is_new_candidate:
            # 新規候補者を作成
            # 空文字列はデフォルト値に置き換え
            gender = self.cleaned_data.get('gender') or GenderChoices.UNSPECIFIED
            employment_status = self.cleaned_data.get('employment_status') or EmploymentStatusChoices.EMPLOYED

            candidate = Candidate.objects.create(
                tenant=self.tenant,
                name=self.cleaned_data['name'],
                name_kana=self.cleaned_data.get('name_kana', ''),
                email=self.cleaned_data['email'],
                phone=self.cleaned_data.get('phone', ''),
                gender=gender,
                birth_date=self.cleaned_data.get('birth_date'),
                address=self.cleaned_data.get('address', ''),
                current_company=self.cleaned_data.get('current_company', ''),
                current_position=self.cleaned_data.get('current_position', ''),
                employment_status=employment_status,
                years_of_experience=self.cleaned_data.get('years_of_experience'),
                desired_salary=self.cleaned_data.get('desired_salary'),
                available_from=self.cleaned_data.get('available_from'),
                skills=skills,
                qualifications=qualifications,
                education=self.cleaned_data.get('education', ''),
                resume_url=self.cleaned_data.get('resume_url') or None,
                cv_url=self.cleaned_data.get('cv_url') or None,
                notes=self.cleaned_data.get('notes', ''),
                registered_by=self.user,
                # エージェントユーザーの場合、エージェント会社を設定
                agent_company=getattr(self.user.profile, 'agent_company', None) if hasattr(self.user, 'profile') else None,
            )
        else:
            candidate = self._existing_candidate

        # 応募を作成
        application = Application.objects.create(
            tenant=self.tenant,
            candidate=candidate,
            job=self.cleaned_data['job'],
            source=self.cleaned_data.get('source'),
            registered_by=self.user,
            notes=self.cleaned_data.get('notes', ''),
        )

        # 初期ステータス履歴を記録
        # 新規応募の場合、from_statusはto_statusと同じにする（履歴の開始点）
        ApplicationStatusHistory.objects.create(
            tenant=self.tenant,
            application=application,
            from_status=application.status,
            to_status=application.status,
            changed_by=self.user,
            notes='統合応募フォームから登録'
        )

        return candidate, application, is_new_candidate

    @property
    def existing_candidate(self):
        """既存候補者（存在する場合）"""
        return self._existing_candidate
