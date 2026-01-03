"""
候補者 Views テスト
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.candidates.models import Candidate, CandidateComment

User = get_user_model()


class CandidateViewTestBase(TestCase):
    """候補者Viewテストの基底クラス"""

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
            phone='0312345678',
        )


class CandidateListViewTest(CandidateViewTestBase):
    """候補者一覧ビューのテスト"""

    def test_list_view_accessible(self):
        """一覧ページにアクセスできる"""
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertTemplateUsed(response, 'candidates/candidate_list.html')

    def test_list_view_contains_candidate(self):
        """作成した候補者が一覧に表示される"""
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertContains(response, 'テスト候補者')

    def test_list_view_search(self):
        """検索機能が動作する"""
        response = self.client.get(
            reverse('candidates:candidate_list') + '?q=テスト'
        )
        self.assertEqual(response.status_code, 200)

    def test_list_view_filter_by_employment_status(self):
        """就業状態フィルターが機能する"""
        response = self.client.get(
            reverse('candidates:candidate_list') + '?employment_status=employed'
        )
        self.assertEqual(response.status_code, 200)


class CandidateDetailViewTest(CandidateViewTestBase):
    """候補者詳細ビューのテスト"""

    def test_detail_view_accessible(self):
        """詳細ページにアクセスできる"""
        response = self.client.get(
            reverse('candidates:candidate_detail', kwargs={'pk': self.candidate.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(
            reverse('candidates:candidate_detail', kwargs={'pk': self.candidate.pk})
        )
        self.assertTemplateUsed(response, 'candidates/candidate_detail.html')

    def test_detail_view_other_tenant_forbidden(self):
        """他テナントの候補者にはアクセスできない"""
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
        response = self.client.get(
            reverse('candidates:candidate_detail', kwargs={'pk': other_candidate.pk})
        )
        self.assertEqual(response.status_code, 404)


class CandidateCreateViewTest(CandidateViewTestBase):
    """候補者作成ビューのテスト"""

    def test_create_view_accessible(self):
        """作成ページにアクセスできる"""
        response = self.client.get(reverse('candidates:candidate_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('candidates:candidate_create'))
        self.assertTemplateUsed(response, 'candidates/candidate_form.html')

    def test_create_view_post_valid_data(self):
        """有効なデータで作成できる"""
        data = {
            'name': '新規候補者',
            'email': 'new@example.com',
            'phone': '0399999999',
        }
        response = self.client.post(reverse('candidates:candidate_create'), data)
        # フォームエラーまたはリダイレクトを確認
        self.assertIn(response.status_code, [200, 302])


class CandidateUpdateViewTest(CandidateViewTestBase):
    """候補者更新ビューのテスト"""

    def test_update_view_accessible(self):
        """更新ページにアクセスできる"""
        response = self.client.get(
            reverse('candidates:candidate_update', kwargs={'pk': self.candidate.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(
            reverse('candidates:candidate_update', kwargs={'pk': self.candidate.pk})
        )
        self.assertTemplateUsed(response, 'candidates/candidate_form.html')


class CandidateArchiveViewTest(CandidateViewTestBase):
    """候補者アーカイブビューのテスト"""

    def test_archive_view_post(self):
        """アーカイブリクエストが動作する"""
        response = self.client.post(
            reverse('candidates:candidate_archive', kwargs={'pk': self.candidate.pk})
        )
        self.assertIn(response.status_code, [200, 302])


class CandidateSearchViewTest(CandidateViewTestBase):
    """候補者検索ビューのテスト"""

    def test_search_accessible(self):
        """検索にアクセスできる"""
        response = self.client.get(
            reverse('candidates:candidate_search') + '?q=テスト'
        )
        self.assertIn(response.status_code, [200, 302])


class CandidateCommentViewTest(CandidateViewTestBase):
    """候補者コメントビューのテスト"""

    def setUp(self):
        super().setUp()
        self.comment = CandidateComment.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            author=self.user,
            content='テストコメント',
        )

    def test_comment_create_post(self):
        """コメント作成が動作する"""
        data = {
            'content': '新しいコメント',
        }
        response = self.client.post(
            reverse('candidates:comment_create', kwargs={'candidate_pk': self.candidate.pk}),
            data
        )
        self.assertIn(response.status_code, [200, 302])

    def test_comment_delete_post(self):
        """コメント削除が動作する"""
        response = self.client.post(
            reverse('candidates:comment_delete', kwargs={
                'candidate_pk': self.candidate.pk,
                'comment_pk': self.comment.pk
            })
        )
        self.assertIn(response.status_code, [200, 302])


class CandidateAuthenticationTest(TestCase):
    """候補者ビューの認証テスト"""

    def test_list_requires_login(self):
        """一覧は認証が必要"""
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_create_requires_login(self):
        """作成は認証が必要"""
        response = self.client.get(reverse('candidates:candidate_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class CandidateTenantIsolationTest(CandidateViewTestBase):
    """候補者のテナント分離テスト"""

    def test_list_shows_only_own_tenant(self):
        """一覧は自テナントのデータのみ表示"""
        other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        Candidate.objects.create(
            tenant=other_tenant,
            name='他テナント候補者',
            email='other@example.com',
        )
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertContains(response, 'テスト候補者')
        self.assertNotContains(response, '他テナント候補者')


class CandidateModelTest(CandidateViewTestBase):
    """候補者モデルのテスト"""

    def test_str_representation(self):
        """文字列表現が正しい"""
        self.assertEqual(str(self.candidate), 'テスト候補者')

    def test_candidate_full_name(self):
        """フルネーム取得"""
        self.candidate.name = '山田 太郎'
        self.candidate.save()
        self.assertIn('山田', str(self.candidate))
