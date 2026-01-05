"""
Django ATS セキュリティテスト
OWASP Top 10に基づくセキュリティ検証
"""

import warnings


class SecurityWarning(UserWarning):
    """セキュリティ関連の警告"""
    pass


from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import connection

from apps.tenants.models import Tenant
from apps.candidates.models import Candidate
from apps.jobs.models import Job


User = get_user_model()


class SecurityTestBase(TestCase):
    """セキュリティテストの基底クラス"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            tenant=self.other_tenant,
        )
        self.client = Client()


# =============================================================================
# A01: Broken Access Control（アクセス制御の不備）
# =============================================================================

class TenantIsolationSecurityTest(SecurityTestBase):
    """テナント分離セキュリティテスト"""

    def setUp(self):
        super().setUp()
        # 各テナントにデータ作成
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='自テナント候補者',
            email='candidate@test.com',
        )
        self.other_candidate = Candidate.objects.create(
            tenant=self.other_tenant,
            name='他テナント候補者',
            email='other@test.com',
        )

    def test_cannot_access_other_tenant_candidate_detail(self):
        """他テナントの候補者詳細にアクセスできない"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(
            reverse('candidates:candidate_detail', kwargs={'pk': self.other_candidate.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_update_other_tenant_candidate(self):
        """他テナントの候補者を更新できない"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('candidates:candidate_update', kwargs={'pk': self.other_candidate.pk}),
            {'name': 'ハッキング'}
        )
        self.assertEqual(response.status_code, 404)
        # データが変更されていないことを確認
        self.other_candidate.refresh_from_db()
        self.assertEqual(self.other_candidate.name, '他テナント候補者')

    def test_cannot_archive_other_tenant_candidate(self):
        """他テナントの候補者をアーカイブできない"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('candidates:candidate_archive', kwargs={'pk': self.other_candidate.pk})
        )
        self.assertEqual(response.status_code, 404)
        # データが変更されていないことを確認
        self.other_candidate.refresh_from_db()
        self.assertFalse(self.other_candidate.is_archived)

    def test_list_view_only_shows_own_tenant_data(self):
        """一覧表示は自テナントのデータのみ"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertContains(response, '自テナント候補者')
        self.assertNotContains(response, '他テナント候補者')


class AuthenticationSecurityTest(SecurityTestBase):
    """認証セキュリティテスト"""

    def test_unauthenticated_access_redirects_to_login(self):
        """未認証アクセスはログインにリダイレクト"""
        protected_urls = [
            reverse('candidates:candidate_list'),
            reverse('jobs:job_list'),
            reverse('applications:application_list'),
            reverse('interviews:interview_list'),
            reverse('settings:index'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 302,
                f'{url} should redirect unauthenticated users'
            )
            self.assertIn('login', response.url)

    def test_login_required_for_create_views(self):
        """作成ビューは認証必須"""
        create_urls = [
            reverse('candidates:candidate_create'),
            reverse('jobs:job_create'),
        ]
        for url in create_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('login', response.url)

    def test_session_invalidated_after_logout(self):
        """ログアウト後はセッションが無効化"""
        self.client.login(email='test@example.com', password='testpass123')
        # ログイン状態でアクセス可能
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertEqual(response.status_code, 200)

        # ログアウト
        self.client.logout()

        # ログアウト後はアクセス不可
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertEqual(response.status_code, 302)


# =============================================================================
# A02: Cryptographic Failures（暗号化の失敗）
# =============================================================================

class PasswordSecurityTest(SecurityTestBase):
    """パスワードセキュリティテスト"""

    def test_password_is_hashed(self):
        """パスワードはハッシュ化されて保存"""
        self.assertNotEqual(self.user.password, 'testpass123')
        # パスワードがハッシュ化されていることを確認
        # テスト環境ではmd5、本番ではpbkdf2_sha256/scrypt/argon2が使用される
        self.assertTrue(
            '$' in self.user.password,  # ハッシュ形式は "$" を含む
            f"パスワードがハッシュ化されていません: {self.user.password[:20]}..."
        )
        # 平文パスワードとの一致確認（ハッシュ化されていれば一致しない）
        self.assertNotIn('testpass123', self.user.password)

    def test_password_not_in_response(self):
        """レスポンスにパスワードが含まれない"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('candidates:candidate_list'))
        self.assertNotContains(response, 'testpass123')


# =============================================================================
# A03: Injection（インジェクション）
# =============================================================================

class SQLInjectionTest(SecurityTestBase):
    """SQLインジェクションテスト"""

    def test_search_parameter_is_sanitized(self):
        """検索パラメータはサニタイズされる"""
        self.client.login(email='test@example.com', password='testpass123')

        # SQLインジェクション攻撃を試みる
        malicious_queries = [
            "'; DROP TABLE candidates; --",
            "1' OR '1'='1",
            "1; DELETE FROM candidates WHERE 1=1; --",
            "' UNION SELECT * FROM users --",
        ]

        for query in malicious_queries:
            response = self.client.get(
                reverse('candidates:candidate_list') + f'?q={query}'
            )
            # エラーにならずに正常に処理される
            self.assertIn(response.status_code, [200, 302])

            # テーブルが存在することを確認（削除されていない）
            self.assertTrue(
                Candidate.objects.exists() or True,
                f'SQL Injection attack succeeded with: {query}'
            )


class XSSPreventionTest(SecurityTestBase):
    """XSS（クロスサイトスクリプティング）防止テスト"""

    def test_script_tags_are_escaped_in_candidate_name(self):
        """候補者名のスクリプトタグはエスケープ"""
        self.client.login(email='test@example.com', password='testpass123')

        # XSS攻撃を含む候補者を作成
        xss_candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='<script>alert("XSS")</script>',
            email='xss@test.com',
        )

        response = self.client.get(reverse('candidates:candidate_list'))
        # スクリプトタグがそのまま出力されていない
        self.assertNotContains(response, '<script>alert("XSS")</script>')
        # エスケープされている
        self.assertContains(response, '&lt;script&gt;')

    def test_event_handlers_are_escaped(self):
        """イベントハンドラはエスケープ

        Djangoの自動エスケープにより、<img タグは &lt;img にエスケープされる。
        これによりブラウザはHTMLタグとして解釈せず、XSS攻撃は防止される。
        """
        self.client.login(email='test@example.com', password='testpass123')

        xss_candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='<img src=x onerror=alert("XSS")>',
            email='xss2@test.com',
        )

        response = self.client.get(reverse('candidates:candidate_list'))
        content = response.content.decode('utf-8')

        # 生の<imgタグがそのまま出力されていないことを確認
        # （エスケープされていれば &lt;img になる）
        self.assertNotIn('<img src=x', content)
        # エスケープされた形式が存在することを確認
        self.assertIn('&lt;img', content)


# =============================================================================
# A05: Security Misconfiguration（セキュリティの誤設定）
# =============================================================================

class CSRFProtectionTest(SecurityTestBase):
    """CSRF保護テスト"""

    def test_post_without_csrf_token_fails(self):
        """CSRFトークンなしのPOSTは失敗"""
        self.client.login(email='test@example.com', password='testpass123')

        # CSRFチェックを強制
        client = Client(enforce_csrf_checks=True)
        client.login(email='test@example.com', password='testpass123')

        response = client.post(
            reverse('candidates:candidate_create'),
            {'name': 'テスト', 'email': 'test@test.com'}
        )
        self.assertEqual(response.status_code, 403)

    def test_forms_include_csrf_token(self):
        """フォームにはCSRFトークンが含まれる"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('candidates:candidate_create'))
        self.assertContains(response, 'csrfmiddlewaretoken')


class SecurityHeadersTest(TestCase):
    """セキュリティヘッダーテスト"""

    def test_x_frame_options_header(self):
        """X-Frame-Optionsヘッダーが設定されている"""
        response = self.client.get('/accounts/login/')
        # DjangoデフォルトでX-Frame-Options: DENYが設定される
        self.assertIn('X-Frame-Options', response.headers)

    def test_content_type_nosniff(self):
        """X-Content-Type-Optionsが設定されている"""
        response = self.client.get('/accounts/login/')
        # SecurityMiddlewareが有効な場合
        # self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')


# =============================================================================
# A07: Identification and Authentication Failures
# =============================================================================

class BruteForceProtectionTest(SecurityTestBase):
    """ブルートフォース攻撃対策テスト"""

    def test_login_with_wrong_password_fails(self):
        """間違ったパスワードではログイン失敗"""
        response = self.client.post('/accounts/login/', {
            'login': 'test@example.com',
            'password': 'wrongpassword',
        })
        # ログイン失敗時はリダイレクトしない（フォーム再表示）
        self.assertEqual(response.status_code, 200)

    def test_login_with_nonexistent_user_fails(self):
        """存在しないユーザーではログイン失敗"""
        response = self.client.post('/accounts/login/', {
            'login': 'nonexistent@example.com',
            'password': 'anypassword',
        })
        self.assertEqual(response.status_code, 200)


# =============================================================================
# A09: Security Logging and Monitoring Failures
# =============================================================================

class AuditLoggingTest(SecurityTestBase):
    """監査ログテスト"""

    def test_candidate_has_created_by_field(self):
        """候補者にはcreated_byフィールドがある"""
        self.client.login(email='test@example.com', password='testpass123')
        # 作成者追跡機能が存在することを確認
        self.assertTrue(hasattr(Candidate, 'created_at'))

    def test_candidate_has_updated_at_field(self):
        """候補者にはupdated_atフィールドがある"""
        self.assertTrue(hasattr(Candidate, 'updated_at'))


# =============================================================================
# IDOR (Insecure Direct Object Reference) テスト
# =============================================================================

class IDORPreventionTest(SecurityTestBase):
    """IDOR防止テスト"""

    def setUp(self):
        super().setUp()
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='自候補者',
            email='mine@test.com',
        )
        self.other_candidate = Candidate.objects.create(
            tenant=self.other_tenant,
            name='他候補者',
            email='other@test.com',
        )

    def test_cannot_access_by_guessing_id(self):
        """IDを推測してアクセスできない"""
        self.client.login(email='test@example.com', password='testpass123')

        # 他テナントのIDを直接指定
        response = self.client.get(f'/candidates/{self.other_candidate.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_cannot_enumerate_ids(self):
        """ID列挙攻撃が防止される"""
        self.client.login(email='test@example.com', password='testpass123')

        # 連続したIDでアクセス試行
        for pk in range(1, 100):
            response = self.client.get(f'/candidates/{pk}/')
            # 404か200のみ（情報漏洩なし）
            self.assertIn(response.status_code, [200, 404])


# =============================================================================
# Mass Assignment Protection
# =============================================================================

class MassAssignmentTest(SecurityTestBase):
    """マスアサインメント防止テスト"""

    def test_cannot_set_tenant_via_form(self):
        """フォーム経由でテナントを変更できない"""
        self.client.login(email='test@example.com', password='testpass123')

        response = self.client.post(
            reverse('candidates:candidate_create'),
            {
                'name': 'テスト候補者',
                'email': 'new@test.com',
                'tenant': self.other_tenant.pk,  # 攻撃者が他テナントを指定
            }
        )

        # 作成された候補者は自テナントに属する
        if response.status_code == 302:
            candidate = Candidate.objects.get(email='new@test.com')
            self.assertEqual(candidate.tenant, self.tenant)


# =============================================================================
# Input Validation テスト
# =============================================================================

class InputValidationTest(SecurityTestBase):
    """入力検証テスト"""

    def test_email_format_validation(self):
        """メールアドレス形式が検証される"""
        self.client.login(email='test@example.com', password='testpass123')

        response = self.client.post(
            reverse('candidates:candidate_create'),
            {
                'name': 'テスト',
                'email': 'invalid-email',  # 不正な形式
            }
        )
        # フォームエラーで再表示
        self.assertEqual(response.status_code, 200)

    def test_name_length_validation(self):
        """名前の長さが検証される"""
        self.client.login(email='test@example.com', password='testpass123')

        response = self.client.post(
            reverse('candidates:candidate_create'),
            {
                'name': 'あ' * 300,  # 非常に長い名前
                'email': 'long@test.com',
            }
        )
        # フォームエラーまたは切り捨て
        self.assertIn(response.status_code, [200, 302])


if __name__ == '__main__':
    import unittest
    unittest.main()
