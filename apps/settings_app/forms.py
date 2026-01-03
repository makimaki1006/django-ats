"""Django ATS - 設定フォーム

StatusSetting, ApplicationSource, EmailTemplate, SpreadsheetConnection用フォーム
"""

import re

from django import forms

from .models import (
    StatusSetting, StatusCategoryChoices,
    ApplicationSource, SourceTypeChoices,
    EmailTemplate,
    SpreadsheetConnection,
)


# =============================================================================
# StatusSetting フォーム
# =============================================================================

class StatusSettingForm(forms.ModelForm):
    """ステータス設定フォーム"""

    class Meta:
        model = StatusSetting
        fields = [
            'category', 'name', 'code', 'display_order',
            'color', 'is_active', 'is_terminal', 'description',
        ]
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '例: 書類選考中',
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '例: screening',
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
            }),
            'color': forms.Select(
                choices=[
                    ('gray', 'グレー'),
                    ('blue', '青'),
                    ('green', '緑'),
                    ('yellow', '黄色'),
                    ('red', '赤'),
                    ('purple', '紫'),
                    ('pink', 'ピンク'),
                    ('indigo', 'インディゴ'),
                    ('cyan', 'シアン'),
                    ('orange', 'オレンジ'),
                ],
                attrs={
                    'class': 'form-select',
                },
            ),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'is_terminal': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'このステータスの説明',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        code = cleaned_data.get('code')

        if category and code and self.tenant:
            # 同じカテゴリ・コードの重複チェック
            queryset = StatusSetting.objects.filter(
                tenant=self.tenant,
                category=category,
                code=code,
            )
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError(
                    f'このカテゴリには既に「{code}」というコードが存在します。'
                )

        return cleaned_data


class StatusSettingFilterForm(forms.Form):
    """ステータス設定フィルターフォーム"""

    category = forms.ChoiceField(
        choices=[('', 'すべてのカテゴリ')] + list(StatusCategoryChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )

    is_active = forms.ChoiceField(
        choices=[
            ('', 'すべて'),
            ('true', '有効のみ'),
            ('false', '無効のみ'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )


# =============================================================================
# ApplicationSource フォーム
# =============================================================================

class ApplicationSourceForm(forms.ModelForm):
    """応募経路フォーム"""

    class Meta:
        model = ApplicationSource
        fields = [
            'name', 'source_type', 'url', 'display_order',
            'is_active', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '例: Indeed',
            }),
            'source_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://example.com',
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': '備考',
            }),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant


class ApplicationSourceFilterForm(forms.Form):
    """応募経路フィルターフォーム"""

    source_type = forms.ChoiceField(
        choices=[('', 'すべてのタイプ')] + list(SourceTypeChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )

    is_active = forms.ChoiceField(
        choices=[
            ('', 'すべて'),
            ('true', '有効のみ'),
            ('false', '無効のみ'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )

    scope = forms.ChoiceField(
        choices=[
            ('', 'すべて'),
            ('global', 'グローバルのみ'),
            ('tenant', 'テナント固有のみ'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )


# =============================================================================
# EmailTemplate フォーム
# =============================================================================

class EmailTemplateForm(forms.ModelForm):
    """メールテンプレートフォーム"""

    class Meta:
        model = EmailTemplate
        fields = [
            'name', 'template_type', 'subject', 'body',
            'is_active', 'is_default',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '例: 面接案内メール',
            }),
            'template_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '例: 【{{company_name}}】面接のご案内',
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 12,
                'placeholder': '{{candidate_name}} 様\n\nお世話になっております。\n...',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
        }
        help_texts = {
            'subject': '変数: {{candidate_name}}, {{job_title}}, {{company_name}}, {{interview_date}}',
            'body': '変数: {{candidate_name}}, {{job_title}}, {{company_name}}, {{interview_date}}等',
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

    def clean(self):
        cleaned_data = super().clean()
        is_default = cleaned_data.get('is_default')
        template_type = cleaned_data.get('template_type')

        if is_default and template_type and self.tenant:
            # 同じタイプで既にデフォルトがある場合は警告
            queryset = EmailTemplate.objects.filter(
                tenant=self.tenant,
                template_type=template_type,
                is_default=True,
            )
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                # 既存のデフォルトを解除するか確認
                self.existing_default = queryset.first()

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # 既存のデフォルトを解除
        if instance.is_default and hasattr(self, 'existing_default'):
            EmailTemplate.objects.filter(
                tenant=self.tenant,
                template_type=instance.template_type,
                is_default=True,
            ).update(is_default=False)

        if commit:
            instance.save()
        return instance


class EmailTemplateFilterForm(forms.Form):
    """メールテンプレートフィルターフォーム"""

    template_type = forms.ChoiceField(
        choices=[('', 'すべてのタイプ')] + list(EmailTemplate.TemplateTypeChoices.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )

    is_active = forms.ChoiceField(
        choices=[
            ('', 'すべて'),
            ('true', '有効のみ'),
            ('false', '無効のみ'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )


# =============================================================================
# SpreadsheetConnection フォーム
# =============================================================================

class SpreadsheetConnectionForm(forms.ModelForm):
    """スプレッドシート連携フォーム"""

    spreadsheet_url = forms.URLField(
        required=True,
        widget=forms.URLInput(attrs={
            'class': 'form-input',
            'placeholder': 'https://docs.google.com/spreadsheets/d/xxxxx/edit',
        }),
        label='スプレッドシートURL',
        help_text='Google SpreadsheetのURLを貼り付けてください',
    )

    class Meta:
        model = SpreadsheetConnection
        fields = [
            'spreadsheet_url', 'spreadsheet_name', 'credentials_json',
            'is_active', 'sync_candidates', 'sync_jobs',
            'sync_applications', 'sync_interviews',
            'auto_sync_enabled', 'sync_interval_minutes',
        ]
        widgets = {
            'spreadsheet_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '例: 採用管理シート',
            }),
            'credentials_json': forms.Textarea(attrs={
                'class': 'form-textarea font-mono text-sm',
                'rows': 8,
                'placeholder': '{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'sync_candidates': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'sync_jobs': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'sync_applications': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'sync_interviews': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'auto_sync_enabled': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'sync_interval_minutes': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '60',
            }),
        }
        help_texts = {
            'credentials_json': 'Google Cloud Consoleからダウンロードしたサービスアカウントキー（JSON形式）',
            'auto_sync_enabled': 'アプリ側の変更を自動的にスプレッドシートに反映します',
            'sync_interval_minutes': 'スプレッドシートからの変更を取り込む間隔（分）',
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

    def clean_spreadsheet_url(self):
        """スプレッドシートURLからIDを抽出"""
        url = self.cleaned_data.get('spreadsheet_url', '')

        # Google SpreadsheetのURLからIDを抽出
        # 例: https://docs.google.com/spreadsheets/d/1abc123xyz/edit
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)

        if not match:
            raise forms.ValidationError(
                'Google SpreadsheetのURLを正しく入力してください。'
                '形式: https://docs.google.com/spreadsheets/d/xxxxx/edit'
            )

        # IDをインスタンスに設定
        self.spreadsheet_id = match.group(1)
        return url

    def clean_credentials_json(self):
        """認証情報JSONの検証"""
        import json
        credentials = self.cleaned_data.get('credentials_json', '')

        if not credentials:
            raise forms.ValidationError('認証情報を入力してください。')

        try:
            data = json.loads(credentials)
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing = [f for f in required_fields if f not in data]
            if missing:
                raise forms.ValidationError(
                    f'認証情報に必要なフィールドがありません: {", ".join(missing)}'
                )
        except json.JSONDecodeError:
            raise forms.ValidationError('認証情報が有効なJSON形式ではありません。')

        return credentials

    def clean(self):
        cleaned_data = super().clean()

        # スプレッドシートIDの重複チェック
        if hasattr(self, 'spreadsheet_id') and self.tenant:
            queryset = SpreadsheetConnection.objects.filter(
                tenant=self.tenant,
                spreadsheet_id=self.spreadsheet_id,
            )
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError(
                    'このスプレッドシートは既に連携されています。'
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.spreadsheet_id = self.spreadsheet_id
        if commit:
            instance.save()
        return instance
