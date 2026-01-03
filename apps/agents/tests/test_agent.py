"""
Agents アプリのモデルテスト

逆証明によるロジック検証:
1. エージェント会社作成
2. グローバル/テナント固有の区別
3. 契約有効期間判定
4. 採用率計算
5. 統計更新
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.tenants.models import Tenant
from apps.agents.models import AgentCompany


class AgentCompanyModelTest(TestCase):
    """エージェント会社モデルのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_create_global_agent(self):
        """グローバルエージェント作成（tenant=null）"""
        agent = AgentCompany.objects.create(
            name='グローバル人材',
            code='GLOBAL001',
            contact_email='contact@global.com',
            fee_rate=Decimal('30.00'),
        )
        self.assertTrue(agent.is_global)
        self.assertIsNone(agent.tenant)
        self.assertTrue(agent.is_active)

    def test_create_tenant_agent(self):
        """テナント固有エージェント作成"""
        agent = AgentCompany.objects.create(
            tenant=self.tenant,
            name='テナント専属人材',
            code='TENANT001',
            contact_email='contact@tenant.com',
            fee_rate=Decimal('25.00'),
        )
        self.assertFalse(agent.is_global)
        self.assertEqual(agent.tenant, self.tenant)

    def test_unique_code(self):
        """コードの一意制約"""
        AgentCompany.objects.create(
            name='エージェント1',
            code='AGT001',
            fee_rate=Decimal('30.00'),
        )

        with self.assertRaises(Exception):  # IntegrityError or ValidationError
            AgentCompany.objects.create(
                name='エージェント2',
                code='AGT001',  # 重複
                fee_rate=Decimal('30.00'),
            )

    def test_is_contract_active_within_period(self):
        """契約有効期間内"""
        today = date.today()
        agent = AgentCompany.objects.create(
            name='エージェント',
            code='AGT001',
            fee_rate=Decimal('30.00'),
            contract_start_date=today - timedelta(days=30),
            contract_end_date=today + timedelta(days=30),
        )
        self.assertTrue(agent.is_contract_active)

    def test_is_contract_active_before_start(self):
        """契約開始前"""
        today = date.today()
        agent = AgentCompany.objects.create(
            name='エージェント',
            code='AGT002',
            fee_rate=Decimal('30.00'),
            contract_start_date=today + timedelta(days=10),  # 未来
            contract_end_date=today + timedelta(days=100),
        )
        self.assertFalse(agent.is_contract_active)

    def test_is_contract_active_after_end(self):
        """契約終了後"""
        today = date.today()
        agent = AgentCompany.objects.create(
            name='エージェント',
            code='AGT003',
            fee_rate=Decimal('30.00'),
            contract_start_date=today - timedelta(days=100),
            contract_end_date=today - timedelta(days=10),  # 過去
        )
        self.assertFalse(agent.is_contract_active)

    def test_is_contract_active_no_dates(self):
        """契約日未設定は有効"""
        agent = AgentCompany.objects.create(
            name='エージェント',
            code='AGT004',
            fee_rate=Decimal('30.00'),
        )
        self.assertTrue(agent.is_contract_active)

    def test_placement_rate_calculation(self):
        """採用率計算"""
        agent = AgentCompany.objects.create(
            name='エージェント',
            code='AGT005',
            fee_rate=Decimal('30.00'),
            total_candidates=100,
            total_placements=25,
        )
        self.assertEqual(agent.placement_rate, 25.0)

    def test_placement_rate_zero_candidates(self):
        """候補者0の場合の採用率"""
        agent = AgentCompany.objects.create(
            name='エージェント',
            code='AGT006',
            fee_rate=Decimal('30.00'),
            total_candidates=0,
            total_placements=0,
        )
        self.assertEqual(agent.placement_rate, 0)

    def test_fee_rate_validator_min(self):
        """手数料率バリデーター（最小）"""
        agent = AgentCompany(
            name='エージェント',
            code='AGT007',
            fee_rate=Decimal('-1.00'),  # 0未満
        )
        with self.assertRaises(ValidationError):
            agent.full_clean()

    def test_fee_rate_validator_max(self):
        """手数料率バリデーター（最大）"""
        agent = AgentCompany(
            name='エージェント',
            code='AGT008',
            fee_rate=Decimal('101.00'),  # 100超
        )
        with self.assertRaises(ValidationError):
            agent.full_clean()

    def test_fee_rate_valid_range(self):
        """有効な手数料率範囲"""
        agent = AgentCompany.objects.create(
            name='エージェント',
            code='AGT009',
            fee_rate=Decimal('35.50'),
        )
        self.assertEqual(agent.fee_rate, Decimal('35.50'))

    def test_preferred_partner_flag(self):
        """優先パートナーフラグ"""
        agent = AgentCompany.objects.create(
            name='優先エージェント',
            code='AGT010',
            fee_rate=Decimal('30.00'),
            is_preferred=True,
        )
        self.assertTrue(agent.is_preferred)

    def test_str_representation(self):
        """__str__の検証"""
        agent = AgentCompany.objects.create(
            name='テスト人材株式会社',
            code='AGT011',
            fee_rate=Decimal('30.00'),
        )
        self.assertEqual(str(agent), 'テスト人材株式会社')

    def test_default_values(self):
        """デフォルト値の確認"""
        agent = AgentCompany.objects.create(
            name='デフォルトエージェント',
            code='AGT012',
        )
        self.assertEqual(agent.fee_rate, Decimal('30.00'))
        self.assertTrue(agent.is_active)
        self.assertFalse(agent.is_preferred)
        self.assertEqual(agent.total_candidates, 0)
        self.assertEqual(agent.total_placements, 0)
