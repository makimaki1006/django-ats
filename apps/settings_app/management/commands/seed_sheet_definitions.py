"""
シート定義シーダーコマンド

全テナントまたは指定テナントにデフォルトのシート定義を作成する。

使用方法:
    # 全テナントにシート定義を作成
    python manage.py seed_sheet_definitions

    # 特定のテナントIDを指定
    python manage.py seed_sheet_definitions --tenant-id 123

    # 既存の定義を上書き
    python manage.py seed_sheet_definitions --force
"""

from django.core.management.base import BaseCommand, CommandError

from apps.tenants.models import Tenant
from apps.settings_app.models import SheetDefinition


class Command(BaseCommand):
    help = 'テナントにデフォルトのシート定義を作成する'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            type=int,
            help='対象テナントのID（省略時は全テナント）',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存の定義を上書きする',
        )

    def handle(self, *args, **options):
        tenant_id = options.get('tenant_id')
        force = options.get('force', False)

        if tenant_id:
            try:
                tenants = [Tenant.objects.get(id=tenant_id)]
            except Tenant.DoesNotExist:
                raise CommandError(f'テナントID {tenant_id} が見つかりません')
        else:
            tenants = Tenant.objects.filter(is_active=True)

        if not tenants:
            self.stdout.write(self.style.WARNING('対象テナントがありません'))
            return

        self.stdout.write(f'対象テナント数: {len(tenants)}')

        # デフォルト定義を取得
        default_definitions = SheetDefinition.get_default_definitions()
        self.stdout.write(f'シート定義数: {len(default_definitions)}')

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for tenant in tenants:
            self.stdout.write(f'\n処理中: {tenant.name}')

            for definition in default_definitions:
                entity_type = definition['entity_type']

                # 既存の定義を確認
                existing = SheetDefinition.objects.filter(
                    tenant=tenant,
                    entity_type=entity_type
                ).first()

                if existing:
                    if force:
                        # 上書き更新
                        for key, value in definition.items():
                            if key != 'entity_type':  # entity_typeは変更不可
                                setattr(existing, key, value)
                        existing.save()
                        updated_count += 1
                        self.stdout.write(
                            f'  更新: {entity_type}'
                        )
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            f'  スキップ: {entity_type}（既存）'
                        )
                else:
                    # 新規作成
                    SheetDefinition.objects.create(
                        tenant=tenant,
                        **definition
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  作成: {entity_type}')
                    )

        # サマリー出力
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('完了'))
        self.stdout.write(f'  作成: {created_count}')
        self.stdout.write(f'  更新: {updated_count}')
        self.stdout.write(f'  スキップ: {skipped_count}')
