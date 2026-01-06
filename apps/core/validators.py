"""Django ATS - 共通バリデータ

アプリケーション全体で使用する共通バリデータ。

使用方法:
    from apps.core.validators import validate_phone_number, validate_postal_code

    class MyForm(forms.Form):
        phone = forms.CharField(validators=[validate_phone_number])
        postal_code = forms.CharField(validators=[validate_postal_code])

    # または、モデルで使用
    class MyModel(models.Model):
        phone = models.CharField(validators=[validate_phone_number])
"""

import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


# =========================================================================
# 電話番号バリデータ
# =========================================================================

def validate_phone_number(value: str) -> None:
    """電話番号のバリデーション

    日本の電話番号形式をチェック。
    ハイフン有無は任意。

    Args:
        value: 電話番号文字列

    Raises:
        ValidationError: 形式が不正な場合

    Examples:
        validate_phone_number('090-1234-5678')  # OK
        validate_phone_number('09012345678')  # OK
        validate_phone_number('03-1234-5678')  # OK
        validate_phone_number('0120-123-456')  # OK
    """
    if not value:
        return  # 空の場合はスキップ（requiredは別途指定）

    # ハイフン・スペース・括弧を除去
    cleaned = re.sub(r'[\s\-\(\)]', '', value)

    # 数字のみかチェック
    if not cleaned.isdigit():
        raise ValidationError(
            _('電話番号は数字とハイフンのみ使用できます。'),
            code='invalid_phone'
        )

    # 桁数チェック（10〜11桁）
    if not (10 <= len(cleaned) <= 11):
        raise ValidationError(
            _('電話番号は10〜11桁で入力してください。'),
            code='invalid_phone_length'
        )

    # 先頭が0かチェック
    if not cleaned.startswith('0'):
        raise ValidationError(
            _('電話番号は0から始まる必要があります。'),
            code='invalid_phone_prefix'
        )


phone_number_validator = RegexValidator(
    regex=r'^[\d\-\s\(\)]+$',
    message=_('電話番号の形式が正しくありません。'),
    code='invalid_phone'
)


# =========================================================================
# 郵便番号バリデータ
# =========================================================================

def validate_postal_code(value: str) -> None:
    """日本の郵便番号バリデーション

    ハイフン有無は任意。

    Args:
        value: 郵便番号文字列

    Raises:
        ValidationError: 形式が不正な場合

    Examples:
        validate_postal_code('123-4567')  # OK
        validate_postal_code('1234567')  # OK
    """
    if not value:
        return

    # ハイフンを除去
    cleaned = value.replace('-', '')

    # 7桁の数字かチェック
    if not re.match(r'^\d{7}$', cleaned):
        raise ValidationError(
            _('郵便番号は7桁の数字で入力してください（例: 123-4567）。'),
            code='invalid_postal_code'
        )


postal_code_validator = RegexValidator(
    regex=r'^\d{3}-?\d{4}$',
    message=_('郵便番号の形式が正しくありません（例: 123-4567）。'),
    code='invalid_postal_code'
)


# =========================================================================
# メールアドレスバリデータ
# =========================================================================

def validate_email_domain(allowed_domains: list = None):
    """メールアドレスのドメイン検証バリデータファクトリ

    特定のドメインのみを許可する場合に使用。

    Args:
        allowed_domains: 許可するドメインのリスト

    Returns:
        バリデータ関数

    Examples:
        validate = validate_email_domain(['example.com', 'company.jp'])
        validate('user@example.com')  # OK
        validate('user@other.com')  # ValidationError
    """
    def validator(value: str) -> None:
        if not value or not allowed_domains:
            return

        if '@' not in value:
            raise ValidationError(
                _('有効なメールアドレスを入力してください。'),
                code='invalid_email'
            )

        domain = value.split('@')[1].lower()
        if domain not in [d.lower() for d in allowed_domains]:
            raise ValidationError(
                _('このドメインのメールアドレスは使用できません。'),
                code='invalid_email_domain'
            )

    return validator


# =========================================================================
# 年齢・生年月日バリデータ
# =========================================================================

def validate_age_range(min_age: int = 0, max_age: int = 120):
    """年齢範囲バリデータファクトリ

    Args:
        min_age: 最小年齢
        max_age: 最大年齢

    Returns:
        バリデータ関数
    """
    def validator(value) -> None:
        from datetime import date

        if not value:
            return

        today = date.today()
        age = today.year - value.year
        if (today.month, today.day) < (value.month, value.day):
            age -= 1

        if age < min_age:
            raise ValidationError(
                _('%(min_age)s歳以上である必要があります。'),
                code='age_too_young',
                params={'min_age': min_age}
            )

        if age > max_age:
            raise ValidationError(
                _('生年月日が正しくありません。'),
                code='age_too_old'
            )

    return validator


def validate_birth_date(value) -> None:
    """生年月日バリデータ

    将来の日付や不合理な過去の日付をチェック。
    """
    from datetime import date

    if not value:
        return

    today = date.today()

    if value > today:
        raise ValidationError(
            _('生年月日は過去の日付を入力してください。'),
            code='future_date'
        )

    # 120年以上前は不合理
    min_year = today.year - 120
    if value.year < min_year:
        raise ValidationError(
            _('生年月日が正しくありません。'),
            code='invalid_birth_date'
        )


# =========================================================================
# 給与・金額バリデータ
# =========================================================================

def validate_salary_range(value: int) -> None:
    """給与範囲バリデータ

    日本の一般的な給与範囲をチェック。
    """
    if value is None:
        return

    min_salary = 0
    max_salary = 100_000_000  # 1億円

    if value < min_salary:
        raise ValidationError(
            _('給与は0以上で入力してください。'),
            code='negative_salary'
        )

    if value > max_salary:
        raise ValidationError(
            _('給与の値が大きすぎます。'),
            code='salary_too_high'
        )


def validate_salary_min_max(min_value: int, max_value: int) -> None:
    """給与範囲の最小・最大値チェック

    最小値が最大値を超えていないことを確認。
    """
    if min_value is None or max_value is None:
        return

    if min_value > max_value:
        raise ValidationError(
            _('最低給与は最高給与以下で入力してください。'),
            code='invalid_salary_range'
        )


# =========================================================================
# JSONフィールドバリデータ
# =========================================================================

def validate_json_list(value) -> None:
    """JSON配列バリデータ

    フィールドがリストであることを確認。
    """
    if value is None:
        return

    if not isinstance(value, list):
        raise ValidationError(
            _('配列形式で入力してください。'),
            code='not_a_list'
        )


def validate_json_dict(value) -> None:
    """JSONオブジェクトバリデータ

    フィールドが辞書であることを確認。
    """
    if value is None:
        return

    if not isinstance(value, dict):
        raise ValidationError(
            _('オブジェクト形式で入力してください。'),
            code='not_a_dict'
        )


# =========================================================================
# スプレッドシート関連バリデータ
# =========================================================================

def validate_spreadsheet_id(value: str) -> None:
    """Google SpreadsheetのIDバリデーション

    SpreadsheetのIDは44文字の英数字とアンダースコア。
    """
    if not value:
        return

    # 44文字の英数字・ハイフン・アンダースコア
    if not re.match(r'^[a-zA-Z0-9_-]{40,50}$', value):
        raise ValidationError(
            _('スプレッドシートIDの形式が正しくありません。'),
            code='invalid_spreadsheet_id'
        )


def validate_google_credentials_json(value: str) -> None:
    """Google認証情報JSONのバリデーション

    サービスアカウントのJSONキーが正しい形式か確認。
    """
    import json

    if not value:
        return

    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        raise ValidationError(
            _('JSONの形式が正しくありません。'),
            code='invalid_json'
        )

    required_fields = ['type', 'project_id', 'private_key', 'client_email']
    missing = [f for f in required_fields if f not in data]

    if missing:
        raise ValidationError(
            _('認証情報に必須フィールドがありません: %(fields)s'),
            code='missing_credentials_fields',
            params={'fields': ', '.join(missing)}
        )

    if data.get('type') != 'service_account':
        raise ValidationError(
            _('サービスアカウントの認証情報を指定してください。'),
            code='invalid_credentials_type'
        )


# =========================================================================
# 汎用バリデータ
# =========================================================================

def validate_no_html(value: str) -> None:
    """HTMLタグを含まないことを確認

    XSS対策として、HTMLタグを禁止する場合に使用。
    """
    if not value:
        return

    if re.search(r'<[^>]+>', value):
        raise ValidationError(
            _('HTMLタグは使用できません。'),
            code='html_not_allowed'
        )


def validate_no_script(value: str) -> None:
    """スクリプトタグを含まないことを確認

    scriptタグとjavascript:を禁止。
    """
    if not value:
        return

    if re.search(r'<script|javascript:', value, re.IGNORECASE):
        raise ValidationError(
            _('スクリプトは使用できません。'),
            code='script_not_allowed'
        )


def validate_max_length_bytes(max_bytes: int):
    """バイト数での最大長チェック

    UTF-8でのバイト数を制限する場合に使用。
    """
    def validator(value: str) -> None:
        if not value:
            return

        byte_length = len(value.encode('utf-8'))
        if byte_length > max_bytes:
            raise ValidationError(
                _('入力が長すぎます（最大%(max)sバイト）。'),
                code='too_long_bytes',
                params={'max': max_bytes}
            )

    return validator
