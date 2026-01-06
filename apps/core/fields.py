"""Django ATS - カスタムフィールド

暗号化フィールドなどのカスタムモデルフィールド定義。
"""

import base64
import logging

from django.conf import settings
from django.db import models

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptedTextField(models.TextField):
    """暗号化テキストフィールド

    Fernetを使用してデータを暗号化・復号化するTextFieldの拡張。
    DBには暗号化された状態で保存され、読み出し時に自動で復号化される。

    使用例:
        class MyModel(models.Model):
            secret_data = EncryptedTextField()

    設定:
        settings.pyに ENCRYPTION_KEY を設定する必要があります。
        キー生成方法: Fernet.generate_key().decode()
    """

    description = "暗号化されたテキストフィールド"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_fernet(self):
        """Fernetインスタンスを取得"""
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            raise ValueError(
                "ENCRYPTION_KEY が設定されていません。"
                "settings.py に ENCRYPTION_KEY を追加してください。"
                "キー生成: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
            )
        return Fernet(key.encode() if isinstance(key, str) else key)

    def get_prep_value(self, value):
        """DB保存前に暗号化"""
        if value is None or value == '':
            return value

        try:
            fernet = self._get_fernet()
            encrypted = fernet.encrypt(value.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"暗号化エラー: {e}")
            raise

    def from_db_value(self, value, expression, connection):
        """DB読み出し時に復号化"""
        if value is None or value == '':
            return value

        try:
            fernet = self._get_fernet()
            decrypted_bytes = base64.urlsafe_b64decode(value.encode('utf-8'))
            decrypted = fernet.decrypt(decrypted_bytes)
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("復号化エラー: 無効なトークンまたはキーの不一致")
            # 古いデータ（暗号化前のデータ）の場合はそのまま返す
            # マイグレーション時の互換性のため
            return value
        except Exception as e:
            logger.error(f"復号化エラー: {e}")
            # エラー時は元の値を返す（データ損失防止）
            return value

    def to_python(self, value):
        """Python値への変換"""
        if value is None:
            return value
        return str(value)


def generate_encryption_key():
    """新しい暗号化キーを生成

    使用例:
        from apps.core.fields import generate_encryption_key
        print(generate_encryption_key())

    Returns:
        str: Base64エンコードされた32バイトのキー
    """
    return Fernet.generate_key().decode()
