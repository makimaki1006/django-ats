"""
Agents アプリ逆証明テスト

逆証明（Proof by Contradiction）により、
不正な操作が適切に拒否されることを検証します。

テスト観点:
1. テナント分離 - 他テナントデータへのアクセス制御
2. グローバル/テナント固有スコープ - 正しいスコープ制御
3. バリデーション - 不正な入力の拒否
4. 認証・認可 - 未認証アクセスの拒否
5. 削除制限 - 関連データ存在時の削除拒否
6. 重複チェック - コード重複の拒否
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.agents.models import AgentCompany
from apps.candidates.models import Candidate

User = get_user_model()


class AgentTenantIsolationInverseTest(TestCase):
    """テナント分離の逆証明テスト

    証明: テナント固有エージェントは他テナントからアクセスできないこと
          グローバルエージェントは全テナントから閲覧可能だが編集不可
    """

    def setUp(self):
        # テナントA
        self.tenant_a = Tenant.objects.create(
            name='テナントA',
            code='tenant-a',
            is_active=True,
        )
        self.user_a = User.objects.create_user(
            email='user_a@example.com',
            password='testpass123',
            tenant=self.tenant_a,
        )
        self.agent_a = AgentCompany.objects.create(
            tenant=self.tenant_a,
            name='テナントAのエージェント',
            code='AGENT-A',
            is_active=True,
        )

        # テナントB
        self.tenant_b = Tenant.objects.create(
            name='テナントB',
            code='tenant-b',
            is_active=True,
        )
        self.user_b = User.objects.create_user(
            email='user_b@example.com',
            password='testpass123',
            tenant=self.tenant_b,
        )
        self.agent_b = AgentCompany.objects.create(
            tenant=self.tenant_b,
            name='テナントBのエージェント',
            code='AGENT-B',
            is_active=True,
        )

        # グローバルエージェント（tenant=null）
        self.global_agent = AgentCompany.objects.create(
            tenant=None,
            name='グローバルエージェント',
            code='AGENT-GLOBAL',
            is_active=True,
        )

        self.client = Client()

    def test_cannot_update_other_tenant_agent(self):
        """他テナントのエージェントは更新できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('agents:agent_update', kwargs={'pk': self.agent_b.pk}),
            {'name': '不正な更新', 'code': 'AGENT-B', 'is_active': True}
        )
        self.assertEqual(response.status_code, 404)
        self.agent_b.refresh_from_db()
        self.assertEqual(self.agent_b.name, 'テナントBのエージェント')

    def test_cannot_delete_other_tenant_agent(self):
        """他テナントのエージェントは削除できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('agents:agent_delete', kwargs={'pk': self.agent_b.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(AgentCompany.objects.filter(pk=self.agent_b.pk).exists())

    def test_cannot_update_global_agent(self):
        """グローバルエージェントは更新できない（テナント固有のみ編集可能）"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('agents:agent_update', kwargs={'pk': self.global_agent.pk}),
            {'name': '不正な更新', 'code': 'AGENT-GLOBAL', 'is_active': True}
        )
        self.assertEqual(response.status_code, 404)
        self.global_agent.refresh_from_db()
        self.assertEqual(self.global_agent.name, 'グローバルエージェント')

    def test_cannot_delete_global_agent(self):
        """グローバルエージェントは削除できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('agents:agent_delete', kwargs={'pk': self.global_agent.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(AgentCompany.objects.filter(pk=self.global_agent.pk).exists())

    def test_can_view_global_agent_in_list(self):
        """グローバルエージェントは一覧に表示される"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.get(reverse('agents:agent_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'グローバルエージェント')
        self.assertContains(response, 'テナントAのエージェント')
        self.assertNotContains(response, 'テナントBのエージェント')


class AgentValidationInverseTest(TestCase):
    """バリデーションの逆証明テスト

    証明: 不正な入力が適切に拒否されること
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.existing_agent = AgentCompany.objects.create(
            tenant=self.tenant,
            name='既存エージェント',
            code='EXISTING-001',
            is_active=True,
        )
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_cannot_create_agent_without_name(self):
        """名前なしでエージェントを作成できない"""
        response = self.client.post(
            reverse('agents:agent_create'),
            {'name': '', 'code': 'NEW-001', 'is_active': True}
        )
        self.assertEqual(response.status_code, 200)  # フォーム再表示
        self.assertContains(response, 'このフィールドは必須です')

    def test_cannot_create_agent_with_duplicate_code(self):
        """重複コードでエージェントを作成できない"""
        response = self.client.post(
            reverse('agents:agent_create'),
            {
                'name': '新規エージェント',
                'code': 'EXISTING-001',  # 既存コード
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '既に使用されています')

    def test_cannot_create_agent_with_invalid_contract_dates(self):
        """契約終了日 < 契約開始日でエージェントを作成できない"""
        response = self.client.post(
            reverse('agents:agent_create'),
            {
                'name': '新規エージェント',
                'code': 'NEW-002',
                'contract_start_date': '2025-12-31',
                'contract_end_date': '2025-01-01',  # 開始日より前
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '契約終了日は開始日以降')


class AgentAuthenticationInverseTest(TestCase):
    """認証・認可の逆証明テスト

    証明: 未認証ユーザーはアクセスできないこと
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.agent = AgentCompany.objects.create(
            tenant=self.tenant,
            name='テストエージェント',
            code='TEST-001',
            is_active=True,
        )
        self.client = Client()
        # ログインしない

    def test_unauthenticated_cannot_access_list(self):
        """未認証ユーザーは一覧にアクセスできない"""
        response = self.client.get(reverse('agents:agent_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_access_detail(self):
        """未認証ユーザーは詳細にアクセスできない"""
        response = self.client.get(
            reverse('agents:agent_detail', kwargs={'pk': self.agent.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_create(self):
        """未認証ユーザーはエージェントを作成できない"""
        response = self.client.post(
            reverse('agents:agent_create'),
            {'name': '不正なエージェント', 'code': 'INVALID', 'is_active': True}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_delete(self):
        """未認証ユーザーはエージェントを削除できない"""
        response = self.client.post(
            reverse('agents:agent_delete', kwargs={'pk': self.agent.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.assertTrue(AgentCompany.objects.filter(pk=self.agent.pk).exists())


class AgentDeletionConstraintInverseTest(TestCase):
    """削除制限の逆証明テスト

    証明: 関連データが存在する場合は削除できないこと
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.agent = AgentCompany.objects.create(
            tenant=self.tenant,
            name='関連ありエージェント',
            code='RELATED-001',
            is_active=True,
        )
        # 候補者に紐付ける
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト候補者',
            email='candidate@example.com',
            agent_company=self.agent,
        )

        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_cannot_delete_agent_with_linked_candidates(self):
        """候補者に紐付いているエージェントは削除できない"""
        response = self.client.post(
            reverse('agents:agent_delete', kwargs={'pk': self.agent.pk})
        )
        # エージェントが削除されていないことを確認
        self.assertTrue(AgentCompany.objects.filter(pk=self.agent.pk).exists())


class AgentToggleInverseTest(TestCase):
    """トグル操作の逆証明テスト

    証明: グローバルエージェントのトグルはできないこと
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.global_agent = AgentCompany.objects.create(
            tenant=None,
            name='グローバルエージェント',
            code='GLOBAL-001',
            is_active=True,
            is_preferred=False,
        )
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_cannot_toggle_active_on_global_agent(self):
        """グローバルエージェントの有効/無効は切り替えられない"""
        response = self.client.post(
            reverse('agents:agent_toggle_active', kwargs={'pk': self.global_agent.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.global_agent.refresh_from_db()
        self.assertTrue(self.global_agent.is_active)  # 変更されていない

    def test_cannot_toggle_preferred_on_global_agent(self):
        """グローバルエージェントの優先パートナーは切り替えられない"""
        response = self.client.post(
            reverse('agents:agent_toggle_preferred', kwargs={'pk': self.global_agent.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.global_agent.refresh_from_db()
        self.assertFalse(self.global_agent.is_preferred)  # 変更されていない


class AgentModelConstraintInverseTest(TestCase):
    """モデル制約の逆証明テスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_str_representation(self):
        """文字列表現が正しい"""
        agent = AgentCompany.objects.create(
            tenant=self.tenant,
            name='テストエージェント',
            code='TEST-001',
        )
        self.assertEqual(str(agent), 'テストエージェント')

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        agent = AgentCompany.objects.create(
            tenant=self.tenant,
            name='デフォルトテスト',
            code='DEFAULT-001',
        )
        self.assertTrue(agent.is_active)
        self.assertFalse(agent.is_preferred)
        self.assertEqual(agent.total_candidates, 0)
        self.assertEqual(agent.total_placements, 0)

    def test_statistics_update(self):
        """統計更新メソッドが動作する"""
        agent = AgentCompany.objects.create(
            tenant=self.tenant,
            name='統計テスト',
            code='STATS-001',
        )
        # 候補者を追加
        Candidate.objects.create(
            tenant=self.tenant,
            name='候補者1',
            email='c1@example.com',
            agent_company=agent,
        )
        Candidate.objects.create(
            tenant=self.tenant,
            name='候補者2',
            email='c2@example.com',
            agent_company=agent,
        )
        agent.update_statistics()
        self.assertEqual(agent.total_candidates, 2)
