"""Django ATS - ロギング設定

センシティブ情報をマスクするカスタムログフィルター。
"""

import logging
import re
from typing import List, Tuple


class SensitiveDataFilter(logging.Filter):
    """センシティブ情報をマスクするログフィルター

    パスワード、認証情報、秘密鍵などをログ出力前にマスクする。

    使用方法:
        settings.pyのLOGGING設定に追加:

        LOGGING = {
            'filters': {
                'sensitive_data': {
                    '()': 'apps.core.logging.SensitiveDataFilter',
                },
            },
            'handlers': {
                'console': {
                    'filters': ['sensitive_data'],
                    ...
                },
            },
        }
    """

    # マスク対象のパターン（正規表現, 置換文字列）
    PATTERNS: List[Tuple[str, str]] = [
        # JSON内のパスワード
        (r'"password"\s*:\s*"[^"]*"', '"password": "***MASKED***"'),
        (r"'password'\s*:\s*'[^']*'", "'password': '***MASKED***'"),

        # JSON内の認証情報
        (r'"private_key"\s*:\s*"[^"]*"', '"private_key": "***MASKED***"'),
        (r'"private_key_id"\s*:\s*"[^"]*"', '"private_key_id": "***MASKED***"'),
        (r'"client_email"\s*:\s*"[^"]*"', '"client_email": "***MASKED***"'),
        (r'"client_secret"\s*:\s*"[^"]*"', '"client_secret": "***MASKED***"'),
        (r'"refresh_token"\s*:\s*"[^"]*"', '"refresh_token": "***MASKED***"'),
        (r'"access_token"\s*:\s*"[^"]*"', '"access_token": "***MASKED***"'),

        # credentials_json フィールド
        (r'credentials_json\s*[=:]\s*["\'][^"\']{50,}["\']',
         'credentials_json: "***MASKED***"'),
        (r'credentials_json\s*[=:]\s*\{[^}]{50,}\}',
         'credentials_json: {***MASKED***}'),

        # API キー
        (r'api_key\s*[=:]\s*["\'][^"\']+["\']', 'api_key: "***MASKED***"'),
        (r'apikey\s*[=:]\s*["\'][^"\']+["\']', 'apikey: "***MASKED***"'),
        (r'API_KEY\s*[=:]\s*["\'][^"\']+["\']', 'API_KEY: "***MASKED***"'),

        # 秘密鍵（BEGIN/END形式）
        (r'-----BEGIN [A-Z ]+-----[^-]+-----END [A-Z ]+-----',
         '-----BEGIN ***MASKED*** KEY-----'),

        # Bearer トークン
        (r'Bearer\s+[A-Za-z0-9\-_.~+/]+=*', 'Bearer ***MASKED***'),

        # Basic認証
        (r'Basic\s+[A-Za-z0-9+/]+=*', 'Basic ***MASKED***'),

        # 暗号化キー
        (r'ENCRYPTION_KEY\s*[=:]\s*["\'][^"\']+["\']',
         'ENCRYPTION_KEY: "***MASKED***"'),
        (r'SECRET_KEY\s*[=:]\s*["\'][^"\']+["\']',
         'SECRET_KEY: "***MASKED***"'),

        # メールパスワード
        (r'EMAIL_HOST_PASSWORD\s*[=:]\s*["\'][^"\']+["\']',
         'EMAIL_HOST_PASSWORD: "***MASKED***"'),

        # データベース接続文字列のパスワード部分
        (r'://[^:]+:([^@]+)@', '://***:***MASKED***@'),
    ]

    def __init__(self, name='', patterns=None):
        super().__init__(name)
        self.patterns = patterns or self.PATTERNS
        # 正規表現をコンパイル
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE | re.DOTALL), replacement)
            for pattern, replacement in self.patterns
        ]

    def filter(self, record):
        """ログレコードをフィルタリング"""
        if hasattr(record, 'msg') and record.msg:
            record.msg = self._mask_sensitive_data(str(record.msg))

        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )

        return True

    def _mask_sensitive_data(self, text: str) -> str:
        """テキスト内のセンシティブ情報をマスク"""
        for pattern, replacement in self._compiled_patterns:
            text = pattern.sub(replacement, text)
        return text


class RequestSanitizer:
    """HTTPリクエスト/レスポンスのサニタイズユーティリティ"""

    SENSITIVE_HEADERS = {
        'authorization',
        'cookie',
        'set-cookie',
        'x-api-key',
        'x-auth-token',
    }

    SENSITIVE_FIELDS = {
        'password',
        'password1',
        'password2',
        'oldpassword',
        'new_password',
        'confirm_password',
        'credentials_json',
        'secret',
        'token',
        'api_key',
    }

    @classmethod
    def sanitize_headers(cls, headers: dict) -> dict:
        """ヘッダーからセンシティブ情報を除去"""
        return {
            key: '***MASKED***' if key.lower() in cls.SENSITIVE_HEADERS else value
            for key, value in headers.items()
        }

    @classmethod
    def sanitize_body(cls, body: dict) -> dict:
        """リクエストボディからセンシティブ情報を除去"""
        if not isinstance(body, dict):
            return body

        result = {}
        for key, value in body.items():
            if key.lower() in cls.SENSITIVE_FIELDS:
                result[key] = '***MASKED***'
            elif isinstance(value, dict):
                result[key] = cls.sanitize_body(value)
            elif isinstance(value, list):
                result[key] = [
                    cls.sanitize_body(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
