"""
Candidates アプリのモデルテスト

逆証明によるロジック検証:
1. 候補者作成・一意制約
2. 年齢計算
3. コメント機能（編集・削除）
4. クエリセットのフィルタリング
"""

from datetime import date

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.candidates.models import (
    Candidate, CandidateComment,
    GenderChoices, EmploymentStatusChoices,
)
from apps.agents.models import AgentCompany


User = get_user_model()


class CandidateModelTest(TestCase):
    """候補者モデルのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            tenant=self.tenant,
        )

    def test_create_candidate(self):
        """候補者作成"""
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='山田太郎',
            name_kana='ヤマダタロウ',
            email='yamada@example.com',
            phone='09012345678',
            gender=GenderChoices.MALE,
            employment_status=EmploymentStatusChoices.EMPLOYED,
            registered_by=self.user,
        )
        self.assertEqual(candidate.name, '山田太郎')
        self.assertFalse(candidate.is_archived)

    def test_unique_email_per_tenant(self):
        """同一テナント内でメール一意"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='山田太郎',
            email='yamada@example.com',
        )

        with self.assertRaises(ValidationError):
            Candidate.objects.create(
                tenant=self.tenant,
                name='山田次郎',
                email='yamada@example.com',  # 重複
            )

    def test_same_email_different_tenant_allowed(self):
        """異なるテナントなら同じメールOK"""
        tenant2 = Tenant.objects.create(
            name='テストテナント2',
            code='test-tenant-2',
            is_active=True,
        )

        Candidate.objects.create(
            tenant=self.tenant,
            name='山田太郎',
            email='yamada@example.com',
        )

        candidate2 = Candidate.objects.create(
            tenant=tenant2,
            name='山田太郎',
            email='yamada@example.com',  # 別テナントなのでOK
        )
        self.assertIsNotNone(candidate2.id)

    def test_age_calculation(self):
        """年齢計算"""
        # 今日から30年前の誕生日
        from django.utils import timezone
        today = timezone.now().date()
        birth_date = date(today.year - 30, today.month, today.day)

        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test@example.com',
            birth_date=birth_date,
        )
        self.assertEqual(candidate.age, 30)

    def test_age_calculation_before_birthday(self):
        """年齢計算（誕生日前）"""
        from django.utils import timezone
        today = timezone.now().date()
        # 来月が誕生日
        if today.month == 12:
            birth_month = 1
            birth_year = today.year - 29
        else:
            birth_month = today.month + 1
            birth_year = today.year - 30

        birth_date = date(birth_year, birth_month, min(today.day, 28))

        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test2@example.com',
            birth_date=birth_date,
        )
        self.assertEqual(candidate.age, 29)  # まだ誕生日前なので29歳

    def test_age_none_if_no_birth_date(self):
        """生年月日なしなら年齢None"""
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test3@example.com',
        )
        self.assertIsNone(candidate.age)

    def test_has_resume(self):
        """履歴書有無"""
        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test4@example.com',
        )
        self.assertFalse(candidate.has_resume)

        candidate.resume_url = 'https://example.com/resume.pdf'
        candidate.save()
        self.assertTrue(candidate.has_resume)

    def test_is_from_agent(self):
        """エージェント経由判定"""
        agent = AgentCompany.objects.create(
            name='テストエージェント',
            code='AGT001',
        )

        candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト',
            email='test5@example.com',
        )
        self.assertFalse(candidate.is_from_agent)

        candidate.agent_company = agent
        candidate.save()
        self.assertTrue(candidate.is_from_agent)

    def test_queryset_active(self):
        """アクティブ候補者クエリ"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='アクティブ',
            email='active@example.com',
            is_archived=False,
        )
        Candidate.objects.create(
            tenant=self.tenant,
            name='アーカイブ',
            email='archived@example.com',
            is_archived=True,
        )

        active = Candidate.objects.active()
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().name, 'アクティブ')

    def test_queryset_archived(self):
        """アーカイブ候補者クエリ"""
        Candidate.objects.create(
            tenant=self.tenant,
            name='アクティブ',
            email='active@example.com',
            is_archived=False,
        )
        Candidate.objects.create(
            tenant=self.tenant,
            name='アーカイブ',
            email='archived@example.com',
            is_archived=True,
        )

        archived = Candidate.objects.archived()
        self.assertEqual(archived.count(), 1)
        self.assertEqual(archived.first().name, 'アーカイブ')


class CandidateCommentTest(TestCase):
    """候補者コメントのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='山田太郎',
            email='yamada@example.com',
        )

    def test_create_comment(self):
        """コメント作成"""
        comment = CandidateComment.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            author=self.user,
            content='良い候補者です。',
        )
        self.assertEqual(comment.content, '良い候補者です。')
        self.assertFalse(comment.is_deleted)
        self.assertFalse(comment.is_edited)

    def test_edit_comment(self):
        """コメント編集"""
        comment = CandidateComment.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            author=self.user,
            content='元のコメント',
        )

        comment.edit('編集後のコメント', self.user)

        self.assertEqual(comment.content, '編集後のコメント')
        self.assertTrue(comment.is_edited)
        self.assertEqual(len(comment.edit_history), 1)
        self.assertEqual(comment.edit_history[0]['previous_content'], '元のコメント')

    def test_edit_by_other_user_denied(self):
        """他人のコメント編集禁止"""
        comment = CandidateComment.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            author=self.user,
            content='コメント',
        )

        with self.assertRaises(PermissionError):
            comment.edit('編集', self.other_user)

    def test_soft_delete(self):
        """論理削除"""
        comment = CandidateComment.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            author=self.user,
            content='コメント',
        )

        comment.soft_delete(self.user)

        self.assertTrue(comment.is_deleted)
        self.assertIsNotNone(comment.deleted_at)
        self.assertEqual(comment.deleted_by, self.user)

    def test_soft_delete_by_other_user_denied(self):
        """他人のコメント削除禁止"""
        comment = CandidateComment.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            author=self.user,
            content='コメント',
        )

        with self.assertRaises(PermissionError):
            comment.soft_delete(self.other_user)

    def test_can_edit(self):
        """編集可能判定"""
        comment = CandidateComment.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            author=self.user,
            content='コメント',
        )

        self.assertTrue(comment.can_edit(self.user))
        self.assertFalse(comment.can_edit(self.other_user))

        comment.soft_delete(self.user)
        self.assertFalse(comment.can_edit(self.user))  # 削除済みは編集不可

    def test_can_delete(self):
        """削除可能判定"""
        comment = CandidateComment.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            author=self.user,
            content='コメント',
        )

        self.assertTrue(comment.can_delete(self.user))
        self.assertFalse(comment.can_delete(self.other_user))

    def test_str_representation(self):
        """__str__の検証"""
        # 30文字より長いコンテンツ
        long_content = 'これは非常に長いコメントで、30文字を超えると省略されるようになっています。確認用。'
        comment = CandidateComment.objects.create(
            tenant=self.tenant,
            candidate=self.candidate,
            author=self.user,
            content=long_content,
        )
        # モデルの実装: content[:30] + '...' if len(content) > 30
        result = str(comment)
        self.assertTrue(result.startswith('admin@example.com:'))
        self.assertIn('...', result)
        # 30文字で切られていることを確認
        self.assertTrue(len(result) < len(f'admin@example.com: {long_content}'))
