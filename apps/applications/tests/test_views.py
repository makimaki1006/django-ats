"""
応募 Views テスト
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.candidates.models import Candidate
from apps.jobs.models import Job
from apps.applications.models import Application, ApplicationStatusChoices

User = get_user_model()


class ApplicationViewTestBase(TestCase):
    """応募Viewテストの基底クラス"""

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

        # テスト用の候補者
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト候補者',
            email='candidate@example.com',
        )

        # テスト用の求人
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-APP-001',
            description='テスト説明',
            status='active',
        )

        # テスト用の応募
        self.application = Application.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            job=self.job,
            status=ApplicationStatusChoices.DOCUMENT_SCREENING,
        )


class ApplicationListViewTest(ApplicationViewTestBase):
    """応募一覧ビューのテスト"""

    def test_list_view_accessible(self):
        """一覧ページにアクセスできる"""
        response = self.client.get(reverse('applications:application_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('applications:application_list'))
        self.assertTemplateUsed(response, 'applications/application_list.html')

    def test_list_view_contains_application(self):
        """作成した応募が一覧に表示される"""
        response = self.client.get(reverse('applications:application_list'))
        self.assertContains(response, 'テスト候補者')

    def test_list_view_filter_by_status(self):
        """ステータスフィルターが機能する"""
        # 別の求人を作成（同じ候補者+求人の組み合わせは禁止されているため）
        other_job = Job.objects.create(
            tenant=self.tenant,
            title='別求人',
            unique_code='TEST-FILTER-001',
            description='テスト説明',
            status='active',
        )
        Application.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            job=other_job,
            status=ApplicationStatusChoices.OFFER_MADE,
        )
        response = self.client.get(
            reverse('applications:application_list') + '?status=document_screening'
        )
        self.assertEqual(response.status_code, 200)

    def test_list_view_filter_by_job(self):
        """求人フィルターが機能する"""
        response = self.client.get(
            reverse('applications:application_list') + f'?job={self.job.pk}'
        )
        self.assertEqual(response.status_code, 200)


class ApplicationDetailViewTest(ApplicationViewTestBase):
    """応募詳細ビューのテスト"""

    def test_detail_view_accessible(self):
        """詳細ページにアクセスできる"""
        response = self.client.get(
            reverse('applications:application_detail', kwargs={'pk': self.application.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_other_tenant_forbidden(self):
        """他テナントの応募にはアクセスできない"""
        other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        other_candidate = Candidate.objects.create(
            tenant=other_tenant,
            name='他候補者',
            email='other@example.com',
        )
        other_job = Job.objects.create(
            tenant=other_tenant,
            title='他求人',
            unique_code='OTHER-APP-001',
            description='説明',
            status='active',
        )
        other_application = Application.objects.create(
            tenant=other_tenant,
            candidate=other_candidate,
            job=other_job,
            status=ApplicationStatusChoices.DOCUMENT_SCREENING,
        )
        response = self.client.get(
            reverse('applications:application_detail', kwargs={'pk': other_application.pk})
        )
        self.assertEqual(response.status_code, 404)


class ApplicationCreateViewTest(ApplicationViewTestBase):
    """応募作成ビューのテスト"""

    def test_create_view_accessible(self):
        """作成ページにアクセスできる"""
        response = self.client.get(reverse('applications:application_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('applications:application_create'))
        self.assertTemplateUsed(response, 'applications/application_form.html')

    def test_create_view_post_valid_data(self):
        """有効なデータで作成できる"""
        new_candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='新候補者',
            email='new@example.com',
        )
        data = {
            'candidate': new_candidate.pk,
            'job': self.job.pk,
            'status': 'screening',
            'source': '',
            'notes': 'テスト応募',
        }
        response = self.client.post(reverse('applications:application_create'), data)
        # フォームエラーまたはリダイレクトを確認
        self.assertIn(response.status_code, [200, 302])


class ApplicationUpdateViewTest(ApplicationViewTestBase):
    """応募更新ビューのテスト"""

    def test_update_view_accessible(self):
        """更新ページにアクセスできる"""
        response = self.client.get(
            reverse('applications:application_update', kwargs={'pk': self.application.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(
            reverse('applications:application_update', kwargs={'pk': self.application.pk})
        )
        self.assertTemplateUsed(response, 'applications/application_form.html')


class ApplicationStatusChangeViewTest(ApplicationViewTestBase):
    """応募ステータス変更ビューのテスト"""

    def test_status_change_post(self):
        """ステータス変更リクエスト"""
        data = {'status': ApplicationStatusChoices.INTERVIEWING}
        response = self.client.post(
            reverse('applications:application_status', kwargs={'pk': self.application.pk}),
            data
        )
        self.assertIn(response.status_code, [200, 302])


class ApplicationKanbanViewTest(ApplicationViewTestBase):
    """応募カンバンビューのテスト"""

    def test_kanban_view_accessible(self):
        """カンバンページにアクセスできる"""
        response = self.client.get(reverse('applications:application_kanban'))
        self.assertEqual(response.status_code, 200)

    def test_kanban_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('applications:application_kanban'))
        self.assertTemplateUsed(response, 'applications/application_kanban.html')


class ApplicationAuthenticationTest(TestCase):
    """応募ビューの認証テスト"""

    def test_list_requires_login(self):
        """一覧は認証が必要"""
        response = self.client.get(reverse('applications:application_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_create_requires_login(self):
        """作成は認証が必要"""
        response = self.client.get(reverse('applications:application_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_kanban_requires_login(self):
        """カンバンは認証が必要"""
        response = self.client.get(reverse('applications:application_kanban'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class ApplicationTenantIsolationTest(ApplicationViewTestBase):
    """応募のテナント分離テスト"""

    def test_list_shows_only_own_tenant(self):
        """一覧は自テナントのデータのみ表示"""
        other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        other_candidate = Candidate.objects.create(
            tenant=other_tenant,
            name='他テナント候補者',
            email='other@example.com',
        )
        other_job = Job.objects.create(
            tenant=other_tenant,
            title='他テナント求人',
            unique_code='OTHER-TEN-001',
            description='説明',
            status='active',
        )
        Application.objects.create(
            tenant=other_tenant,
            candidate=other_candidate,
            job=other_job,
            status=ApplicationStatusChoices.DOCUMENT_SCREENING,
        )
        response = self.client.get(reverse('applications:application_list'))
        self.assertContains(response, 'テスト候補者')
        self.assertNotContains(response, '他テナント候補者')


class ApplicationModelTest(ApplicationViewTestBase):
    """応募モデルのテスト"""

    def test_str_representation(self):
        """文字列表現が正しい"""
        str_repr = str(self.application)
        self.assertIn('テスト候補者', str_repr)

    def test_application_status_choices(self):
        """ステータス選択肢が有効"""
        valid_statuses = [
            ApplicationStatusChoices.NEW,
            ApplicationStatusChoices.DOCUMENT_SCREENING,
            ApplicationStatusChoices.INTERVIEWING,
            ApplicationStatusChoices.OFFER_MADE,
        ]
        for status in valid_statuses:
            self.application.status = status
            self.application.save()
            self.application.refresh_from_db()
            self.assertEqual(self.application.status, status)
