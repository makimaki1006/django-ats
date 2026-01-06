"""バリデータのテスト

apps/core/validators.py のテスト。
"""

import pytest
from datetime import date
from django.core.exceptions import ValidationError

from apps.core.validators import (
    validate_phone_number,
    validate_postal_code,
    validate_email_domain,
    validate_age_range,
    validate_birth_date,
    validate_salary_range,
    validate_salary_min_max,
    validate_json_list,
    validate_json_dict,
    validate_spreadsheet_id,
    validate_google_credentials_json,
    validate_no_html,
    validate_no_script,
    validate_max_length_bytes,
    phone_number_validator,
    postal_code_validator,
)


# =========================================================================
# 電話番号バリデータのテスト
# =========================================================================

class TestValidatePhoneNumber:
    """電話番号バリデータのテスト"""

    def test_valid_mobile_with_hyphen(self):
        """ハイフン付き携帯電話番号"""
        validate_phone_number('090-1234-5678')

    def test_valid_mobile_without_hyphen(self):
        """ハイフンなし携帯電話番号"""
        validate_phone_number('09012345678')

    def test_valid_landline_with_hyphen(self):
        """ハイフン付き固定電話番号"""
        validate_phone_number('03-1234-5678')

    def test_valid_toll_free(self):
        """フリーダイヤル"""
        validate_phone_number('0120-123-456')

    def test_valid_with_parenthesis(self):
        """括弧付き"""
        validate_phone_number('(03)1234-5678')

    def test_empty_value(self):
        """空の値はスキップ"""
        validate_phone_number('')
        validate_phone_number(None)

    def test_invalid_non_numeric(self):
        """数字以外の文字を含む"""
        with pytest.raises(ValidationError) as exc:
            validate_phone_number('090-abcd-5678')
        assert exc.value.code == 'invalid_phone'

    def test_invalid_too_short(self):
        """桁数不足"""
        with pytest.raises(ValidationError) as exc:
            validate_phone_number('090-123')
        assert exc.value.code == 'invalid_phone_length'

    def test_invalid_too_long(self):
        """桁数超過"""
        with pytest.raises(ValidationError) as exc:
            validate_phone_number('090-1234-56789-0')
        assert exc.value.code == 'invalid_phone_length'

    def test_invalid_not_starting_with_zero(self):
        """0始まりでない"""
        with pytest.raises(ValidationError) as exc:
            validate_phone_number('190-1234-5678')
        assert exc.value.code == 'invalid_phone_prefix'


# =========================================================================
# 郵便番号バリデータのテスト
# =========================================================================

class TestValidatePostalCode:
    """郵便番号バリデータのテスト"""

    def test_valid_with_hyphen(self):
        """ハイフン付き"""
        validate_postal_code('123-4567')

    def test_valid_without_hyphen(self):
        """ハイフンなし"""
        validate_postal_code('1234567')

    def test_empty_value(self):
        """空の値はスキップ"""
        validate_postal_code('')
        validate_postal_code(None)

    def test_invalid_too_short(self):
        """桁数不足"""
        with pytest.raises(ValidationError) as exc:
            validate_postal_code('123-456')
        assert exc.value.code == 'invalid_postal_code'

    def test_invalid_too_long(self):
        """桁数超過"""
        with pytest.raises(ValidationError) as exc:
            validate_postal_code('123-45678')
        assert exc.value.code == 'invalid_postal_code'

    def test_invalid_non_numeric(self):
        """数字以外を含む"""
        with pytest.raises(ValidationError) as exc:
            validate_postal_code('abc-defg')
        assert exc.value.code == 'invalid_postal_code'


# =========================================================================
# メールドメインバリデータのテスト
# =========================================================================

class TestValidateEmailDomain:
    """メールドメインバリデータのテスト"""

    def test_valid_domain(self):
        """許可ドメイン"""
        validator = validate_email_domain(['example.com', 'company.jp'])
        validator('user@example.com')

    def test_valid_domain_case_insensitive(self):
        """大文字小文字を区別しない"""
        validator = validate_email_domain(['Example.com'])
        validator('user@example.COM')

    def test_empty_value(self):
        """空の値はスキップ"""
        validator = validate_email_domain(['example.com'])
        validator('')
        validator(None)

    def test_empty_domains(self):
        """許可ドメインが空"""
        validator = validate_email_domain([])
        validator('user@any.com')

    def test_invalid_domain(self):
        """許可されていないドメイン"""
        validator = validate_email_domain(['example.com'])
        with pytest.raises(ValidationError) as exc:
            validator('user@other.com')
        assert exc.value.code == 'invalid_email_domain'

    def test_invalid_email_format(self):
        """@がない"""
        validator = validate_email_domain(['example.com'])
        with pytest.raises(ValidationError) as exc:
            validator('user.example.com')
        assert exc.value.code == 'invalid_email'


# =========================================================================
# 年齢バリデータのテスト
# =========================================================================

class TestValidateAgeRange:
    """年齢範囲バリデータのテスト"""

    def test_valid_age(self):
        """有効な年齢"""
        validator = validate_age_range(min_age=18, max_age=65)
        # 30歳の生年月日
        birth_date = date.today().replace(year=date.today().year - 30)
        validator(birth_date)

    def test_empty_value(self):
        """空の値はスキップ"""
        validator = validate_age_range(min_age=18, max_age=65)
        validator(None)

    def test_age_too_young(self):
        """最低年齢未満"""
        validator = validate_age_range(min_age=18, max_age=65)
        # 10歳の生年月日
        birth_date = date.today().replace(year=date.today().year - 10)
        with pytest.raises(ValidationError) as exc:
            validator(birth_date)
        assert exc.value.code == 'age_too_young'

    def test_age_too_old(self):
        """最高年齢超過"""
        validator = validate_age_range(min_age=18, max_age=65)
        # 130歳の生年月日
        birth_date = date.today().replace(year=date.today().year - 130)
        with pytest.raises(ValidationError) as exc:
            validator(birth_date)
        assert exc.value.code == 'age_too_old'


class TestValidateBirthDate:
    """生年月日バリデータのテスト"""

    def test_valid_birth_date(self):
        """有効な生年月日"""
        birth_date = date(1990, 1, 15)
        validate_birth_date(birth_date)

    def test_empty_value(self):
        """空の値はスキップ"""
        validate_birth_date(None)

    def test_future_date(self):
        """未来の日付"""
        future_date = date.today().replace(year=date.today().year + 1)
        with pytest.raises(ValidationError) as exc:
            validate_birth_date(future_date)
        assert exc.value.code == 'future_date'

    def test_too_old(self):
        """120年以上前"""
        old_date = date.today().replace(year=date.today().year - 130)
        with pytest.raises(ValidationError) as exc:
            validate_birth_date(old_date)
        assert exc.value.code == 'invalid_birth_date'


# =========================================================================
# 給与バリデータのテスト
# =========================================================================

class TestValidateSalaryRange:
    """給与範囲バリデータのテスト"""

    def test_valid_salary(self):
        """有効な給与"""
        validate_salary_range(5_000_000)

    def test_zero_salary(self):
        """0円"""
        validate_salary_range(0)

    def test_none_value(self):
        """Noneはスキップ"""
        validate_salary_range(None)

    def test_negative_salary(self):
        """マイナス"""
        with pytest.raises(ValidationError) as exc:
            validate_salary_range(-100)
        assert exc.value.code == 'negative_salary'

    def test_too_high_salary(self):
        """1億円超過"""
        with pytest.raises(ValidationError) as exc:
            validate_salary_range(200_000_000)
        assert exc.value.code == 'salary_too_high'


class TestValidateSalaryMinMax:
    """給与最小・最大値バリデータのテスト"""

    def test_valid_range(self):
        """有効な範囲"""
        validate_salary_min_max(3_000_000, 5_000_000)

    def test_same_values(self):
        """同じ値"""
        validate_salary_min_max(5_000_000, 5_000_000)

    def test_none_values(self):
        """Noneはスキップ"""
        validate_salary_min_max(None, 5_000_000)
        validate_salary_min_max(3_000_000, None)
        validate_salary_min_max(None, None)

    def test_invalid_range(self):
        """最小値 > 最大値"""
        with pytest.raises(ValidationError) as exc:
            validate_salary_min_max(5_000_000, 3_000_000)
        assert exc.value.code == 'invalid_salary_range'


# =========================================================================
# JSONバリデータのテスト
# =========================================================================

class TestValidateJsonList:
    """JSON配列バリデータのテスト"""

    def test_valid_list(self):
        """有効なリスト"""
        validate_json_list([1, 2, 3])
        validate_json_list(['a', 'b', 'c'])
        validate_json_list([])

    def test_none_value(self):
        """Noneはスキップ"""
        validate_json_list(None)

    def test_invalid_dict(self):
        """辞書は不可"""
        with pytest.raises(ValidationError) as exc:
            validate_json_list({'key': 'value'})
        assert exc.value.code == 'not_a_list'

    def test_invalid_string(self):
        """文字列は不可"""
        with pytest.raises(ValidationError) as exc:
            validate_json_list('string')
        assert exc.value.code == 'not_a_list'


class TestValidateJsonDict:
    """JSONオブジェクトバリデータのテスト"""

    def test_valid_dict(self):
        """有効な辞書"""
        validate_json_dict({'key': 'value'})
        validate_json_dict({})

    def test_none_value(self):
        """Noneはスキップ"""
        validate_json_dict(None)

    def test_invalid_list(self):
        """リストは不可"""
        with pytest.raises(ValidationError) as exc:
            validate_json_dict([1, 2, 3])
        assert exc.value.code == 'not_a_dict'


# =========================================================================
# スプレッドシート関連バリデータのテスト
# =========================================================================

class TestValidateSpreadsheetId:
    """スプレッドシートIDバリデータのテスト"""

    def test_valid_id(self):
        """有効なID（44文字の英数字）"""
        validate_spreadsheet_id('1abc123ABC_-' + 'x' * 30)

    def test_empty_value(self):
        """空の値はスキップ"""
        validate_spreadsheet_id('')
        validate_spreadsheet_id(None)

    def test_too_short(self):
        """短すぎる"""
        with pytest.raises(ValidationError) as exc:
            validate_spreadsheet_id('abc123')
        assert exc.value.code == 'invalid_spreadsheet_id'

    def test_invalid_characters(self):
        """無効な文字を含む"""
        with pytest.raises(ValidationError) as exc:
            validate_spreadsheet_id('abc@#$%' + 'x' * 40)
        assert exc.value.code == 'invalid_spreadsheet_id'


class TestValidateGoogleCredentialsJson:
    """Google認証情報JSONバリデータのテスト"""

    def test_valid_credentials(self):
        """有効な認証情報"""
        import json
        credentials = {
            'type': 'service_account',
            'project_id': 'my-project',
            'private_key': 'key-content',
            'client_email': 'service@project.iam.gserviceaccount.com'
        }
        validate_google_credentials_json(json.dumps(credentials))

    def test_empty_value(self):
        """空の値はスキップ"""
        validate_google_credentials_json('')
        validate_google_credentials_json(None)

    def test_invalid_json(self):
        """無効なJSON"""
        with pytest.raises(ValidationError) as exc:
            validate_google_credentials_json('not-valid-json')
        assert exc.value.code == 'invalid_json'

    def test_missing_fields(self):
        """必須フィールドがない"""
        import json
        credentials = {'type': 'service_account'}
        with pytest.raises(ValidationError) as exc:
            validate_google_credentials_json(json.dumps(credentials))
        assert exc.value.code == 'missing_credentials_fields'

    def test_wrong_type(self):
        """typeがservice_accountでない"""
        import json
        credentials = {
            'type': 'authorized_user',  # 誤り
            'project_id': 'my-project',
            'private_key': 'key-content',
            'client_email': 'email@example.com'
        }
        with pytest.raises(ValidationError) as exc:
            validate_google_credentials_json(json.dumps(credentials))
        assert exc.value.code == 'invalid_credentials_type'


# =========================================================================
# 汎用バリデータのテスト
# =========================================================================

class TestValidateNoHtml:
    """HTMLタグ禁止バリデータのテスト"""

    def test_valid_text(self):
        """HTMLなし"""
        validate_no_html('Hello, World!')
        validate_no_html('価格は<100円です')  # 不等号は許可

    def test_empty_value(self):
        """空の値はスキップ"""
        validate_no_html('')
        validate_no_html(None)

    def test_html_tag(self):
        """HTMLタグを含む"""
        with pytest.raises(ValidationError) as exc:
            validate_no_html('<b>Bold</b>')
        assert exc.value.code == 'html_not_allowed'

    def test_script_tag(self):
        """scriptタグ"""
        with pytest.raises(ValidationError) as exc:
            validate_no_html('<script>alert("XSS")</script>')
        assert exc.value.code == 'html_not_allowed'


class TestValidateNoScript:
    """スクリプト禁止バリデータのテスト"""

    def test_valid_text(self):
        """スクリプトなし"""
        validate_no_script('Hello, World!')

    def test_empty_value(self):
        """空の値はスキップ"""
        validate_no_script('')
        validate_no_script(None)

    def test_script_tag(self):
        """scriptタグ"""
        with pytest.raises(ValidationError) as exc:
            validate_no_script('<script>alert("XSS")</script>')
        assert exc.value.code == 'script_not_allowed'

    def test_javascript_protocol(self):
        """javascript:プロトコル"""
        with pytest.raises(ValidationError) as exc:
            validate_no_script('javascript:alert("XSS")')
        assert exc.value.code == 'script_not_allowed'

    def test_case_insensitive(self):
        """大文字小文字を区別しない"""
        with pytest.raises(ValidationError) as exc:
            validate_no_script('<SCRIPT>alert("XSS")</SCRIPT>')
        assert exc.value.code == 'script_not_allowed'


class TestValidateMaxLengthBytes:
    """バイト数制限バリデータのテスト"""

    def test_valid_length(self):
        """制限内"""
        validator = validate_max_length_bytes(100)
        validator('Hello, World!')

    def test_empty_value(self):
        """空の値はスキップ"""
        validator = validate_max_length_bytes(10)
        validator('')
        validator(None)

    def test_japanese_characters(self):
        """日本語（3バイト/文字）"""
        validator = validate_max_length_bytes(12)
        validator('あいうえ')  # 12バイト
        with pytest.raises(ValidationError) as exc:
            validator('あいうえお')  # 15バイト
        assert exc.value.code == 'too_long_bytes'


# =========================================================================
# RegexValidatorのテスト
# =========================================================================

class TestPhoneNumberValidator:
    """phone_number_validator（RegexValidator）のテスト"""

    def test_valid_pattern(self):
        """有効なパターン"""
        phone_number_validator('090-1234-5678')
        phone_number_validator('(03) 1234-5678')

    def test_invalid_pattern(self):
        """無効なパターン"""
        with pytest.raises(ValidationError):
            phone_number_validator('abc-defg-hijk')


class TestPostalCodeValidator:
    """postal_code_validator（RegexValidator）のテスト"""

    def test_valid_pattern(self):
        """有効なパターン"""
        postal_code_validator('123-4567')
        postal_code_validator('1234567')

    def test_invalid_pattern(self):
        """無効なパターン"""
        with pytest.raises(ValidationError):
            postal_code_validator('12-34567')
