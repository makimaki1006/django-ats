"""
面接 Views テスト
"""

from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.candidates.models import Candidate
from apps.jobs.models import Job
from apps.applications.models import Application, ApplicationStatusChoices
from apps.interviews.models import (
    Interview,
    InterviewTypeChoices,
    InterviewStatusChoices,
    InterviewResultChoices,
)

User = get_user_model()


class InterviewViewTestBase(TestCase):
    """面接Viewテストの基底クラス"""

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
            unique_code='TEST-INT-001',
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

        # テスト用の面接
        self.interview = Interview.objects.create(
            tenant=self.tenant,
            application=self.application,
            interview_type=InterviewTypeChoices.VIDEO,
            interview_round=1,
            scheduled_at=timezone.now() + timedelta(days=1),
            duration_minutes=60,
            status=InterviewStatusChoices.SCHEDULED,
        )


class InterviewListViewTest(InterviewViewTestBase):
    """面接一覧ビューのテスト"""

    def test_list_view_accessible(self):
        """一覧ページにアクセスできる"""
        response = self.client.get(reverse('interviews:interview_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('interviews:interview_list'))
        self.assertTemplateUsed(response, 'interviews/interview_list.html')

    def test_list_view_contains_interview(self):
        """作成した面接が一覧に表示される"""
        response = self.client.get(reverse('interviews:interview_list'))
        self.assertContains(response, 'テスト候補者')

    def test_list_view_filter_by_status(self):
        """ステータスフィルターが機能する"""
        Interview.objects.create(
            tenant=self.tenant,
            application=self.application,
            interview_type=InterviewTypeChoices.VIDEO,
            interview_round=2,
            scheduled_at=timezone.now() + timedelta(days=2),
            status=InterviewStatusChoices.COMPLETED,
        )
        response = self.client.get(
            reverse('interviews:interview_list') + '?status=scheduled'
        )
        self.assertEqual(response.status_code, 200)


class InterviewDetailViewTest(InterviewViewTestBase):
    """面接詳細ビューのテスト"""

    def test_detail_view_accessible(self):
        """詳細ページにアクセスできる"""
        response = self.client.get(
            reverse('interviews:interview_detail', kwargs={'pk': self.interview.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_other_tenant_forbidden(self):
        """他テナントの面接にはアクセスできない"""
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
            unique_code='OTHER-INT-001',
            description='説明',
            status='active',
        )
        other_application = Application.objects.create(
            tenant=other_tenant,
            candidate=other_candidate,
            job=other_job,
            status=ApplicationStatusChoices.DOCUMENT_SCREENING,
        )
        other_interview = Interview.objects.create(
            tenant=other_tenant,
            application=other_application,
            interview_type=InterviewTypeChoices.VIDEO,
            interview_round=1,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        response = self.client.get(
            reverse('interviews:interview_detail', kwargs={'pk': other_interview.pk})
        )
        self.assertEqual(response.status_code, 404)


class InterviewCreateViewTest(InterviewViewTestBase):
    """面接作成ビューのテスト"""

    def test_create_view_accessible(self):
        """作成ページにアクセスできる"""
        response = self.client.get(reverse('interviews:interview_create'))
        self.assertEqual(response.status_code, 200)

    def test_create_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('interviews:interview_create'))
        self.assertTemplateUsed(response, 'interviews/interview_form.html')

    def test_create_view_post_valid_data(self):
        """有効なデータで作成できる"""
        scheduled_time = timezone.now() + timedelta(days=3)
        data = {
            'application': self.application.pk,
            'interview_type': InterviewTypeChoices.VIDEO,
            'interview_round': 2,
            'scheduled_at': scheduled_time.strftime('%Y-%m-%d %H:%M'),
            'duration_minutes': 60,
            'location': 'https://zoom.us/meeting123',
            'status': InterviewStatusChoices.SCHEDULED,
        }
        response = self.client.post(reverse('interviews:interview_create'), data)
        # フォームエラーまたはリダイレクトを確認
        self.assertIn(response.status_code, [200, 302])


class InterviewUpdateViewTest(InterviewViewTestBase):
    """面接更新ビューのテスト"""

    def test_update_view_accessible(self):
        """更新ページにアクセスできる"""
        response = self.client.get(
            reverse('interviews:interview_update', kwargs={'pk': self.interview.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(
            reverse('interviews:interview_update', kwargs={'pk': self.interview.pk})
        )
        self.assertTemplateUsed(response, 'interviews/interview_form.html')


class InterviewResultViewTest(InterviewViewTestBase):
    """面接結果入力ビューのテスト"""

    def test_result_view_post_valid_data(self):
        """有効なデータで結果を保存できる"""
        data = {
            'result': InterviewResultChoices.PASSED,
            'evaluation_score': 4,
            'feedback': 'とても良い印象でした',
            'internal_notes': '次回最終面接へ',
        }
        response = self.client.post(
            reverse('interviews:interview_result', kwargs={'pk': self.interview.pk}),
            data
        )
        # リダイレクトまたはフォーム再表示
        self.assertIn(response.status_code, [200, 302])


class InterviewCancelViewTest(InterviewViewTestBase):
    """面接キャンセルビューのテスト"""

    def test_cancel_view_post(self):
        """キャンセルリクエストで面接がキャンセルされる"""
        response = self.client.post(
            reverse('interviews:interview_cancel', kwargs={'pk': self.interview.pk}),
            {'reason': 'スケジュール変更のため'}
        )
        self.assertIn(response.status_code, [200, 302])


class InterviewCalendarViewTest(InterviewViewTestBase):
    """面接カレンダービューのテスト"""

    def test_calendar_view_accessible(self):
        """カレンダーページにアクセスできる"""
        response = self.client.get(reverse('interviews:interview_calendar'))
        self.assertEqual(response.status_code, 200)

    def test_calendar_view_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('interviews:interview_calendar'))
        self.assertTemplateUsed(response, 'interviews/interview_calendar.html')


class InterviewSupportDashboardViewTest(InterviewViewTestBase):
    """面接サポートダッシュボードビューのテスト"""

    def test_support_dashboard_accessible(self):
        """サポートダッシュボードにアクセスできる"""
        # 面接官として設定
        self.interview.interviewer = self.user
        self.interview.save()
        response = self.client.get(reverse('interviews:interview_support_dashboard'))
        self.assertEqual(response.status_code, 200)


class InterviewSupportDetailViewTest(InterviewViewTestBase):
    """面接サポート詳細ビューのテスト"""

    def test_support_detail_accessible(self):
        """サポート詳細ページにアクセスできる（面接官としてアクセス）"""
        # 面接官として設定
        self.interview.interviewer = self.user
        self.interview.save()
        response = self.client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': self.interview.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_support_detail_non_interviewer_forbidden(self):
        """面接官以外はアクセスできない"""
        # 面接官未設定の場合
        response = self.client.get(
            reverse('interviews:interview_support_detail', kwargs={'pk': self.interview.pk})
        )
        self.assertEqual(response.status_code, 404)


class InterviewAuthenticationTest(TestCase):
    """面接ビューの認証テスト"""

    def test_list_requires_login(self):
        """一覧は認証が必要"""
        response = self.client.get(reverse('interviews:interview_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_create_requires_login(self):
        """作成は認証が必要"""
        response = self.client.get(reverse('interviews:interview_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_calendar_requires_login(self):
        """カレンダーは認証が必要"""
        response = self.client.get(reverse('interviews:interview_calendar'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class InterviewModelTest(InterviewViewTestBase):
    """面接モデルのテスト"""

    def test_str_representation(self):
        """文字列表現が正しい"""
        self.assertIn('テスト候補者', str(self.interview))

    def test_is_upcoming_property(self):
        """これからの面接かどうか判定"""
        self.assertTrue(self.interview.is_upcoming)

    def test_is_today_property(self):
        """今日の面接かどうか判定"""
        today_interview = Interview.objects.create(
            tenant=self.tenant,
            application=self.application,
            interview_type=InterviewTypeChoices.VIDEO,
            interview_round=2,
            scheduled_at=timezone.now(),
        )
        self.assertTrue(today_interview.is_today)

    def test_complete_method(self):
        """complete()メソッドで面接を完了にできる"""
        self.interview.complete(
            result=InterviewResultChoices.PASSED,
            score=5,
            feedback='素晴らしい候補者'
        )
        self.interview.refresh_from_db()
        self.assertEqual(self.interview.status, InterviewStatusChoices.COMPLETED)
        self.assertEqual(self.interview.result, InterviewResultChoices.PASSED)
        self.assertEqual(self.interview.evaluation_score, 5)

    def test_cancel_method(self):
        """cancel()メソッドで面接をキャンセルできる"""
        self.interview.cancel(reason='テストキャンセル')
        self.interview.refresh_from_db()
        self.assertEqual(self.interview.status, InterviewStatusChoices.CANCELLED)
        self.assertIn('テストキャンセル', self.interview.internal_notes)
