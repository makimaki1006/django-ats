"""
Django ATS - コアビュー
ダッシュボード、共通ビューなど
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.utils import timezone
from django.views.generic import TemplateView
from datetime import timedelta

from .mixins import HtmxMixin

# キャッシュキー定数
DASHBOARD_STATS_CACHE_KEY = 'dashboard_stats_{tenant_id}'
DASHBOARD_STATS_CACHE_TIMEOUT = 300  # 5分


class DashboardView(LoginRequiredMixin, HtmxMixin, TemplateView):
    """ダッシュボードビュー"""
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        tenant = self.request.tenant

        # 統計データを取得
        context.update(self.get_statistics(tenant))

        # 最近のアクティビティ
        context['recent_activities'] = self.get_recent_activities(tenant)

        # 今後の面接
        context['upcoming_interviews'] = self.get_upcoming_interviews(tenant)

        # クイックアクション（ロールに応じて表示）
        context['quick_actions'] = self.get_quick_actions(user)

        return context

    def get_statistics(self, tenant):
        """統計データを取得（キャッシュ付き）"""
        from apps.candidates.models import Candidate
        from apps.jobs.models import Job
        from apps.applications.models import Application
        from apps.interviews.models import Interview

        stats = {}

        if not tenant:
            return stats

        # キャッシュから取得を試みる
        cache_key = DASHBOARD_STATS_CACHE_KEY.format(tenant_id=tenant.id)
        cached_stats = cache.get(cache_key)
        if cached_stats is not None:
            return cached_stats

        # 応募者数
        try:
            stats['total_candidates'] = Candidate.objects.filter(
                tenant=tenant
            ).count()

            # 今月の新規応募者
            this_month = timezone.now().replace(day=1)
            stats['new_candidates_this_month'] = Candidate.objects.filter(
                tenant=tenant,
                created_at__gte=this_month
            ).count()
        except Exception:
            stats['total_candidates'] = 0
            stats['new_candidates_this_month'] = 0

        # 求人数
        try:
            stats['active_jobs'] = Job.objects.filter(
                tenant=tenant,
                status='published'
            ).count()

            stats['total_jobs'] = Job.objects.filter(
                tenant=tenant
            ).count()
        except Exception:
            stats['active_jobs'] = 0
            stats['total_jobs'] = 0

        # 応募数
        try:
            stats['total_applications'] = Application.objects.filter(
                tenant=tenant
            ).count()

            # 未処理の応募
            stats['pending_applications'] = Application.objects.filter(
                tenant=tenant,
                status='new'
            ).count()
        except Exception:
            stats['total_applications'] = 0
            stats['pending_applications'] = 0

        # 面接数
        try:
            today = timezone.now().date()
            stats['interviews_today'] = Interview.objects.filter(
                tenant=tenant,
                scheduled_at__date=today
            ).count()

            # 今週の面接
            week_end = today + timedelta(days=7)
            stats['interviews_this_week'] = Interview.objects.filter(
                tenant=tenant,
                scheduled_at__date__gte=today,
                scheduled_at__date__lte=week_end
            ).count()
        except Exception:
            stats['interviews_today'] = 0
            stats['interviews_this_week'] = 0

        # キャッシュに保存
        cache.set(cache_key, stats, DASHBOARD_STATS_CACHE_TIMEOUT)

        return stats

    def get_recent_activities(self, tenant, limit=5):
        """最近のアクティビティを取得"""
        from apps.applications.models import Application

        if not tenant:
            return []

        try:
            return Application.objects.filter(
                tenant=tenant
            ).select_related(
                'candidate', 'job'
            ).order_by('-updated_at')[:limit]
        except Exception:
            return []

    def get_upcoming_interviews(self, tenant, limit=5):
        """今後の面接を取得"""
        from apps.interviews.models import Interview

        if not tenant:
            return []

        try:
            now = timezone.now()
            return Interview.objects.filter(
                tenant=tenant,
                scheduled_at__gte=now,
                status='scheduled'
            ).select_related(
                'application__candidate', 'application__job'
            ).order_by('scheduled_at')[:limit]
        except Exception:
            return []

    def get_quick_actions(self, user):
        """ロールに応じたクイックアクションを取得"""
        actions = []

        if user.is_admin:
            actions.extend([
                {
                    'label': '新規ユーザー追加',
                    'url': 'accounts:user_create',
                    'icon': 'user-plus',
                },
                {
                    'label': '求人作成',
                    'url': 'jobs:job_create',
                    'icon': 'briefcase',
                },
            ])

        if user.is_recruiter:
            actions.extend([
                {
                    'label': '応募者登録',
                    'url': 'candidates:candidate_create',
                    'icon': 'user',
                },
                {
                    'label': '面接予約',
                    'url': 'interviews:interview_create',
                    'icon': 'calendar',
                },
            ])

        return actions


class HomeView(TemplateView):
    """ホームページ（未ログイン）"""
    template_name = 'home.html'

    def dispatch(self, request, *args, **kwargs):
        # ログイン済みの場合はダッシュボードへリダイレクト
        if request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
