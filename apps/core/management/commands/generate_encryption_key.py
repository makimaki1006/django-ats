"""Django ATS - 暗号化キー生成コマンド

使用方法:
    python manage.py generate_encryption_key

生成されたキーを .env ファイルに追加してください:
    ENCRYPTION_KEY=生成されたキー
"""

from django.core.management.base import BaseCommand

from cryptography.fernet import Fernet


class Command(BaseCommand):
    help = 'データ暗号化用のキーを生成します'

    def handle(self, *args, **options):
        key = Fernet.generate_key().decode()

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('暗号化キーが生成されました'))
        self.stdout.write('=' * 60 + '\n')

        self.stdout.write(f'ENCRYPTION_KEY={key}')

        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('このキーを .env ファイルに追加してください。')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('注意:'))
        self.stdout.write('- このキーは安全に保管してください')
        self.stdout.write('- キーを変更すると既存の暗号化データが読めなくなります')
        self.stdout.write('- 本番環境と開発環境で異なるキーを使用してください')
        self.stdout.write('-' * 60 + '\n')
