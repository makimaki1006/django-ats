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

    def get_template_names(self):
        """HTMXパーシャルリクエストの場合はパーシャルテンプレートを返す"""
        partial = self.request.GET.get('partial')
        if self.request.htmx and partial == 'stats':
            return ['dashboard/partials/stats_cards.html']
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        tenant = self.request.tenant

        # パーシャルリクエストの場合は統計のみ返す
        partial = self.request.GET.get('partial')
        if self.request.htmx and partial == 'stats':
            # キャッシュを無効化して最新データを取得
            cache_key = DASHBOARD_STATS_CACHE_KEY.format(tenant_id=tenant.id if tenant else 'none')
            cache.delete(cache_key)
            context.update(self.get_statistics(tenant))
            return context

        # 統計データを取得
        context.update(self.get_statistics(tenant))

        # 最近のアクティビティ
        context['recent_activities'] = self.get_recent_activities(tenant)

        # 今後の面接
        context['upcoming_interviews'] = self.get_upcoming_interviews(tenant)

        # クイックアクション（ロールに応じて表示）
        context['quick_actions'] = self.get_quick_actions(user)

        # 追加ウィジェット
        context['funnel_data'] = self.get_funnel_data(tenant)
        context['source_stats'] = self.get_source_stats(tenant)
        context['monthly_trend'] = self.get_monthly_trend(tenant)
        context['performance_metrics'] = self.get_performance_metrics(tenant)

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

    def get_funnel_data(self, tenant):
        """採用ファネルデータを取得"""
        from apps.applications.models import Application
        from django.db.models import Count

        if not tenant:
            return []

        try:
            status_counts = Application.objects.filter(
                tenant=tenant
            ).values('status').annotate(
                count=Count('id')
            ).order_by('status')

            # ファネル順序でソート
            funnel_order = ['new', 'screening', 'interview', 'offered', 'hired', 'rejected', 'withdrawn']
            funnel_labels = {
                'new': '新規応募',
                'screening': '書類選考',
                'interview': '面接中',
                'offered': '内定',
                'hired': '採用',
                'rejected': '不採用',
                'withdrawn': '辞退',
            }

            funnel_data = []
            status_dict = {s['status']: s['count'] for s in status_counts}
            total = sum(status_dict.values()) or 1

            for status in funnel_order:
                count = status_dict.get(status, 0)
                funnel_data.append({
                    'status': status,
                    'label': funnel_labels.get(status, status),
                    'count': count,
                    'percentage': round(count / total * 100, 1),
                })

            return funnel_data
        except Exception:
            return []

    def get_source_stats(self, tenant):
        """応募経路別統計を取得"""
        from apps.applications.models import Application
        from django.db.models import Count

        if not tenant:
            return []

        try:
            source_counts = Application.objects.filter(
                tenant=tenant,
                source__isnull=False
            ).values(
                'source__name'
            ).annotate(
                count=Count('id')
            ).order_by('-count')[:5]

            return [
                {
                    'name': s['source__name'],
                    'count': s['count']
                }
                for s in source_counts
            ]
        except Exception:
            return []

    def get_monthly_trend(self, tenant):
        """月別トレンドデータを取得"""
        from apps.applications.models import Application
        from apps.candidates.models import Candidate
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        from dateutil.relativedelta import relativedelta

        if not tenant:
            return {'months': [], 'applications': [], 'candidates': []}

        try:
            # 過去6ヶ月
            end_date = timezone.now()
            start_date = end_date - relativedelta(months=5)
            start_date = start_date.replace(day=1)

            # 応募数
            app_trend = Application.objects.filter(
                tenant=tenant,
                applied_at__gte=start_date
            ).annotate(
                month=TruncMonth('applied_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')

            # 候補者数
            cand_trend = Candidate.objects.filter(
                tenant=tenant,
                created_at__gte=start_date
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')

            app_dict = {t['month']: t['count'] for t in app_trend}
            cand_dict = {t['month']: t['count'] for t in cand_trend}

            months = []
            applications = []
            candidates = []

            current = start_date
            while current <= end_date:
                month_key = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                months.append(current.strftime('%m月'))
                applications.append(app_dict.get(month_key, 0))
                candidates.append(cand_dict.get(month_key, 0))
                current += relativedelta(months=1)

            return {
                'months': months,
                'applications': applications,
                'candidates': candidates,
            }
        except Exception:
            return {'months': [], 'applications': [], 'candidates': []}

    def get_performance_metrics(self, tenant):
        """パフォーマンス指標を取得"""
        from apps.applications.models import Application
        from apps.interviews.models import Interview
        from django.db.models import Avg, F
        from django.db.models.functions import ExtractDay

        if not tenant:
            return {}

        metrics = {}

        try:
            # 採用率（hired / total）
            total_apps = Application.objects.filter(tenant=tenant).count()
            hired_apps = Application.objects.filter(tenant=tenant, status='hired').count()
            metrics['hire_rate'] = round(hired_apps / total_apps * 100, 1) if total_apps > 0 else 0

            # 面接通過率
            total_interviews = Interview.objects.filter(tenant=tenant, result__isnull=False).count()
            passed_interviews = Interview.objects.filter(tenant=tenant, result='pass').count()
            metrics['interview_pass_rate'] = round(passed_interviews / total_interviews * 100, 1) if total_interviews > 0 else 0

            # 平均応募処理日数（新規→次ステータス）
            # 簡易的に今月の応募で計算
            this_month = timezone.now().replace(day=1)
            recent_apps = Application.objects.filter(
                tenant=tenant,
                applied_at__gte=this_month,
                status__in=['screening', 'interview', 'offered', 'hired', 'rejected']
            )
            if recent_apps.exists():
                avg_days = recent_apps.annotate(
                    days=ExtractDay(F('updated_at') - F('applied_at'))
                ).aggregate(avg=Avg('days'))['avg']
                metrics['avg_processing_days'] = round(avg_days, 1) if avg_days else 0
            else:
                metrics['avg_processing_days'] = 0

            # 内定承諾率
            offered_apps = Application.objects.filter(tenant=tenant, status='offered').count()
            hired_from_offered = Application.objects.filter(tenant=tenant, status='hired').count()
            metrics['offer_acceptance_rate'] = round(hired_from_offered / (offered_apps + hired_from_offered) * 100, 1) if (offered_apps + hired_from_offered) > 0 else 0

        except Exception:
            metrics = {
                'hire_rate': 0,
                'interview_pass_rate': 0,
                'avg_processing_days': 0,
                'offer_acceptance_rate': 0,
            }

        return metrics


class HomeView(TemplateView):
    """ホームページ（未ログイン）"""
    template_name = 'home.html'

    def dispatch(self, request, *args, **kwargs):
        # ログイン済みの場合はダッシュボードへリダイレクト
        if request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
