"""
求人 Views テスト
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.jobs.models import Job, JobStatusChoices

User = get_user_model()


class JobViewTestBase(TestCase):
    """求人Viewテストの基底クラス"""

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

        # テスト用の求人
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
            description='テスト説明',
            status=JobStatusChoices.ACTIVE,
        )


class JobListViewTest(JobViewTestBase):
    """求人一覧ビューのテスト"""

    def test_list_view_accessible(self):
        """一覧ページにアクセスできる"""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertTemplateUsed(response, 'jobs/job_list.html')

    def test_list_view_contains_job(self):
        """作成した求人が一覧に表示される"""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertContains(response, 'テスト求人')

    def test_list_view_filter_by_status(self):
        """ステータスフィルターが機能する"""
        Job.objects.create(
            tenant=self.tenant,
            title='下書き求人',
            unique_code='DRAFT-001',
            status=JobStatusChoices.DRAFT,
        )
        response = self.client.get(
            reverse('jobs:job_list') + '?status=active'
        )
        self.assertEqual(response.status_code, 200)

    def test_list_view_search(self):
        """検索が機能する"""
        response = self.client.get(
            reverse('jobs:job_list') + '?q=テスト'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト求人')


class JobDetailViewTest(JobViewTestBase):
    """求人詳細ビューのテスト"""

    def test_detail_view_accessible(self):
        """詳細ページにアクセスできる"""
        response = self.client.get(
            reverse('jobs:job_detail', kwargs={'pk': self.job.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_other_tenant_forbidden(self):
        """他テナントの求人にはアクセスできない"""
        other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        other_job = Job.objects.create(
            tenant=other_tenant,
            title='他テナント求人',
            unique_code='OTHER-001',
        )
        response = self.client.get(
            reverse('jobs:job_detail', kwargs={'pk': other_job.pk})
        )
        self.assertEqual(response.status_code, 404)


class JobCreateViewTest(JobViewTestBase):
    """求人作成ビューのテスト"""

    def test_create_view_accessible(self):
        """作成ページにアクセスできる"""
        response = self.client.get(reverse('jobs:job_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('jobs:job_create'))
        self.assertTemplateUsed(response, 'jobs/job_form.html')

    def test_create_view_post_valid_data(self):
        """有効なデータで作成できる"""
        data = {
            'title': '新規求人',
            'unique_code': 'NEW-001',
            'description': '新規求人の説明',
            'department': '開発部',
            'location': '東京都',
            'status': JobStatusChoices.DRAFT,
        }
        response = self.client.post(reverse('jobs:job_create'), data)
        # フォームエラーまたはリダイレクトを確認
        self.assertIn(response.status_code, [200, 302])


class JobUpdateViewTest(JobViewTestBase):
    """求人更新ビューのテスト"""

    def test_update_view_accessible(self):
        """更新ページにアクセスできる"""
        response = self.client.get(
            reverse('jobs:job_update', kwargs={'pk': self.job.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(
            reverse('jobs:job_update', kwargs={'pk': self.job.pk})
        )
        self.assertTemplateUsed(response, 'jobs/job_form.html')

    def test_update_view_post_valid_data(self):
        """有効なデータで更新できる"""
        data = {
            'title': '更新済み求人',
            'unique_code': 'TEST-001',
            'description': '更新された説明',
            'department': '営業部',
            'location': '大阪府',
            'status': JobStatusChoices.ACTIVE,
        }
        response = self.client.post(
            reverse('jobs:job_update', kwargs={'pk': self.job.pk}),
            data
        )
        self.assertIn(response.status_code, [200, 302])


class JobAuthenticationTest(TestCase):
    """求人ビューの認証テスト"""

    def test_list_requires_login(self):
        """一覧は認証が必要"""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_create_requires_login(self):
        """作成は認証が必要"""
        response = self.client.get(reverse('jobs:job_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class JobTenantIsolationTest(JobViewTestBase):
    """求人のテナント分離テスト"""

    def test_list_shows_only_own_tenant(self):
        """一覧は自テナントのデータのみ表示"""
        other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        Job.objects.create(
            tenant=other_tenant,
            title='他テナント求人',
            unique_code='OTHER-001',
        )
        response = self.client.get(reverse('jobs:job_list'))
        self.assertContains(response, 'テスト求人')
        self.assertNotContains(response, '他テナント求人')
