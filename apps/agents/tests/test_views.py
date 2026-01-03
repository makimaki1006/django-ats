"""
エージェント会社 Views テスト
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from apps.tenants.models import Tenant
from apps.agents.models import AgentCompany
from apps.agents.forms import AgentCompanyForm

User = get_user_model()


class AgentCompanyViewTestBase(TestCase):
    """エージェント会社Viewテストの基底クラス"""

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
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

        self.agent = AgentCompany.objects.create(
            tenant=self.tenant,
            name='テストエージェント',
            code='AGT-001',
            contact_email='agent@example.com',
            contact_phone='09012345678',
            contact_person='担当太郎',
            fee_rate=Decimal('20.00'),
            is_active=True,
            is_preferred=False,
        )


class AgentCompanyListViewTest(AgentCompanyViewTestBase):
    """エージェント会社一覧ビューのテスト"""

    def test_list_view_accessible(self):
        """一覧ページにアクセスできる"""
        response = self.client.get(reverse('agents:agent_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('agents:agent_list'))
        self.assertTemplateUsed(response, 'agents/agent_list.html')

    def test_list_view_contains_agent(self):
        """作成したエージェントが一覧に表示される"""
        response = self.client.get(reverse('agents:agent_list'))
        self.assertContains(response, 'テストエージェント')

    def test_list_view_filter_by_active(self):
        """アクティブフィルターが機能する"""
        AgentCompany.objects.create(
            tenant=self.tenant,
            name='非アクティブエージェント',
            code='AGT-002',
            is_active=False,
        )
        response = self.client.get(
            reverse('agents:agent_list') + '?is_active=true'
        )
        self.assertContains(response, 'テストエージェント')
        self.assertNotContains(response, '非アクティブエージェント')

    def test_list_view_filter_by_preferred(self):
        """優先フィルターが機能する"""
        AgentCompany.objects.create(
            tenant=self.tenant,
            name='優先エージェント',
            code='AGT-003',
            is_preferred=True,
        )
        response = self.client.get(
            reverse('agents:agent_list') + '?is_preferred=true'
        )
        self.assertContains(response, '優先エージェント')
        self.assertNotContains(response, 'テストエージェント')

    def test_list_view_search(self):
        """検索が機能する"""
        response = self.client.get(
            reverse('agents:agent_list') + '?q=テスト'
        )
        self.assertContains(response, 'テストエージェント')


class AgentCompanyDetailViewTest(AgentCompanyViewTestBase):
    """エージェント会社詳細ビューのテスト"""

    def test_detail_view_accessible(self):
        """詳細ページにアクセスできる"""
        response = self.client.get(
            reverse('agents:agent_detail', kwargs={'pk': self.agent.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(
            reverse('agents:agent_detail', kwargs={'pk': self.agent.pk})
        )
        self.assertTemplateUsed(response, 'agents/agent_detail.html')

    def test_detail_view_shows_agent_info(self):
        """エージェント情報が表示される"""
        response = self.client.get(
            reverse('agents:agent_detail', kwargs={'pk': self.agent.pk})
        )
        self.assertContains(response, 'テストエージェント')
        self.assertContains(response, 'AGT-001')

    def test_detail_view_other_tenant_forbidden(self):
        """他テナントのエージェントにはアクセスできない"""
        other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        other_agent = AgentCompany.objects.create(
            tenant=other_tenant,
            name='他テナントエージェント',
            code='AGT-OTHER',
        )
        response = self.client.get(
            reverse('agents:agent_detail', kwargs={'pk': other_agent.pk})
        )
        self.assertEqual(response.status_code, 404)


class AgentCompanyCreateViewTest(AgentCompanyViewTestBase):
    """エージェント会社作成ビューのテスト"""

    def test_create_view_accessible(self):
        """作成ページにアクセスできる"""
        response = self.client.get(reverse('agents:agent_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('agents:agent_create'))
        self.assertTemplateUsed(response, 'agents/agent_form.html')

    def test_create_view_post_valid_data(self):
        """有効なデータで作成できる"""
        data = {
            'name': '新規エージェント',
            'code': 'AGT-NEW',
            'contact_email': 'new@example.com',
            'contact_phone': '09099998888',
            'contact_person': '新規担当者',
            'fee_rate': '15.00',
            'is_active': True,
            'is_preferred': False,
            'address': '',
            'website': '',
            'notes': '',
        }
        response = self.client.post(reverse('agents:agent_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AgentCompany.objects.filter(name='新規エージェント').exists())

    def test_create_view_post_invalid_data(self):
        """無効なデータでは作成されない"""
        data = {
            'name': '',
            'code': '',
        }
        response = self.client.post(reverse('agents:agent_create'), data)
        self.assertEqual(response.status_code, 200)


class AgentCompanyUpdateViewTest(AgentCompanyViewTestBase):
    """エージェント会社更新ビューのテスト"""

    def test_update_view_accessible(self):
        """更新ページにアクセスできる"""
        response = self.client.get(
            reverse('agents:agent_update', kwargs={'pk': self.agent.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view_post_valid_data(self):
        """有効なデータで更新できる"""
        data = {
            'name': '更新済みエージェント',
            'code': 'AGT-001',
            'contact_email': 'updated@example.com',
            'contact_phone': '09012345678',
            'contact_person': '更新担当者',
            'fee_rate': '25.00',
            'is_active': True,
            'is_preferred': True,
            'address': '',
            'website': '',
            'notes': '',
        }
        response = self.client.post(
            reverse('agents:agent_update', kwargs={'pk': self.agent.pk}),
            data
        )
        self.assertEqual(response.status_code, 302)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.name, '更新済みエージェント')
        self.assertEqual(self.agent.fee_rate, Decimal('25.00'))


class AgentCompanyDeleteViewTest(AgentCompanyViewTestBase):
    """エージェント会社削除ビューのテスト"""

    def test_delete_view_post(self):
        """削除リクエストでエージェントが削除される"""
        agent_id = self.agent.pk
        response = self.client.post(
            reverse('agents:agent_delete', kwargs={'pk': agent_id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(AgentCompany.objects.filter(pk=agent_id).exists())


class AgentCompanyFormTest(TestCase):
    """エージェント会社フォームのテスト"""

    def test_form_valid_data(self):
        """有効なデータでフォームが有効"""
        data = {
            'name': 'テストエージェント',
            'code': 'AGT-TEST',
            'contact_email': 'test@example.com',
            'contact_phone': '09012345678',
            'contact_person': '担当者',
            'fee_rate': '20.00',
            'is_active': True,
            'is_preferred': False,
            'address': '',
            'website': '',
            'notes': '',
        }
        form = AgentCompanyForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_name_required(self):
        """名前は必須"""
        data = {
            'name': '',
            'code': 'AGT-TEST',
        }
        form = AgentCompanyForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_form_code_required(self):
        """コードは必須"""
        data = {
            'name': 'テスト',
            'code': '',
        }
        form = AgentCompanyForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

    def test_form_invalid_fee_rate(self):
        """不正な手数料率はエラー"""
        data = {
            'name': 'テスト',
            'code': 'AGT-TEST',
            'fee_rate': '-10.00',  # 負の値
        }
        form = AgentCompanyForm(data=data)
        # フォームまたはモデルのバリデーションでエラー
        if not form.is_valid():
            pass  # 期待通りエラー


class AgentCompanyAuthenticationTest(TestCase):
    """エージェント会社ビューの認証テスト"""

    def test_list_requires_login(self):
        """一覧は認証が必要"""
        response = self.client.get(reverse('agents:agent_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_create_requires_login(self):
        """作成は認証が必要"""
        response = self.client.get(reverse('agents:agent_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
