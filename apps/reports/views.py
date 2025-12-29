"""
Django ATS - レポートビュー
採用活動の統計情報とレポートを提供
"""

from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncMonth, TruncWeek
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View
import csv

from apps.core.mixins import TenantQuerysetMixin, HtmxMixin
from apps.applications.models import Application, ApplicationStatusChoices
from apps.candidates.models import Candidate
from apps.interviews.models import Interview, InterviewStatusChoices
from apps.jobs.models import Job, JobStatusChoices


class ReportsDashboardView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    TemplateView
):
    """レポートダッシュボード"""
    template_name = 'reports/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        # 期間フィルター
        period = self.request.GET.get('period', '30')
        try:
            days = int(period)
        except ValueError:
            days = 30

        start_date = timezone.now() - timedelta(days=days)

        # 基本統計
        context['stats'] = self._get_basic_stats(tenant, start_date)

        # 応募ステータス分布
        context['application_status_dist'] = self._get_application_status_distribution(tenant, start_date)

        # 月別応募推移
        context['monthly_applications'] = self._get_monthly_applications(tenant)

        # 求人別応募数
        context['job_applications'] = self._get_job_applications(tenant, start_date)

        # 面接結果分布
        context['interview_results'] = self._get_interview_results(tenant, start_date)

        # 選択期間
        context['period'] = period

        return context

    def _get_basic_stats(self, tenant, start_date):
        """基本統計を取得"""
        return {
            'total_candidates': Candidate.objects.filter(tenant=tenant).count(),
            'new_candidates': Candidate.objects.filter(
                tenant=tenant,
                created_at__gte=start_date
            ).count(),
            'total_applications': Application.objects.filter(tenant=tenant).count(),
            'new_applications': Application.objects.filter(
                tenant=tenant,
                applied_at__gte=start_date
            ).count(),
            'active_jobs': Job.objects.filter(
                tenant=tenant,
                status=JobStatusChoices.ACTIVE
            ).count(),
            'scheduled_interviews': Interview.objects.filter(
                tenant=tenant,
                status=InterviewStatusChoices.SCHEDULED
            ).count(),
            'offer_rate': self._calculate_offer_rate(tenant, start_date),
        }

    def _calculate_offer_rate(self, tenant, start_date):
        """内定率を計算"""
        total = Application.objects.filter(
            tenant=tenant,
            applied_at__gte=start_date
        ).count()

        if total == 0:
            return 0

        offers = Application.objects.filter(
            tenant=tenant,
            applied_at__gte=start_date,
            status__in=[
                ApplicationStatusChoices.OFFER_MADE,
                ApplicationStatusChoices.OFFER_ACCEPTED,
            ]
        ).count()

        return round(offers / total * 100, 1)

    def _get_application_status_distribution(self, tenant, start_date):
        """応募ステータス分布を取得"""
        return Application.objects.filter(
            tenant=tenant,
            applied_at__gte=start_date
        ).values('status').annotate(
            count=Count('id')
        ).order_by('-count')

    def _get_monthly_applications(self, tenant):
        """月別応募数を取得（過去6ヶ月）"""
        six_months_ago = timezone.now() - timedelta(days=180)

        return Application.objects.filter(
            tenant=tenant,
            applied_at__gte=six_months_ago
        ).annotate(
            month=TruncMonth('applied_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

    def _get_job_applications(self, tenant, start_date):
        """求人別応募数を取得"""
        return Job.objects.filter(
            tenant=tenant
        ).annotate(
            app_count=Count(
                'applications',
                filter=Q(applications__applied_at__gte=start_date)
            )
        ).filter(
            app_count__gt=0
        ).order_by('-app_count')[:10]

    def _get_interview_results(self, tenant, start_date):
        """面接結果分布を取得"""
        return Interview.objects.filter(
            tenant=tenant,
            scheduled_at__gte=start_date,
            status=InterviewStatusChoices.COMPLETED
        ).values('result').annotate(
            count=Count('id')
        ).order_by('-count')


class ApplicationsReportView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    TemplateView
):
    """応募レポート"""
    template_name = 'reports/applications.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        # 週別応募推移
        three_months_ago = timezone.now() - timedelta(days=90)
        context['weekly_applications'] = Application.objects.filter(
            tenant=tenant,
            applied_at__gte=three_months_ago
        ).annotate(
            week=TruncWeek('applied_at')
        ).values('week').annotate(
            count=Count('id')
        ).order_by('week')

        # ステータス別詳細
        context['status_breakdown'] = Application.objects.filter(
            tenant=tenant
        ).values('status').annotate(
            count=Count('id')
        ).order_by('status')

        # 応募経路別
        context['source_breakdown'] = Application.objects.filter(
            tenant=tenant
        ).values('source__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        return context


class InterviewsReportView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    TemplateView
):
    """面接レポート"""
    template_name = 'reports/interviews.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        # 面接官別件数
        context['interviewer_stats'] = Interview.objects.filter(
            tenant=tenant,
            status=InterviewStatusChoices.COMPLETED
        ).values(
            'interviewer__first_name',
            'interviewer__last_name'
        ).annotate(
            count=Count('id'),
            avg_score=Avg('evaluation_score')
        ).order_by('-count')[:10]

        # 面接タイプ別
        context['type_breakdown'] = Interview.objects.filter(
            tenant=tenant
        ).values('interview_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # 面接結果別
        context['result_breakdown'] = Interview.objects.filter(
            tenant=tenant,
            status=InterviewStatusChoices.COMPLETED
        ).values('result').annotate(
            count=Count('id')
        ).order_by('-count')

        return context


class ExportCSVView(LoginRequiredMixin, TenantQuerysetMixin, View):
    """CSVエクスポート"""

    def get(self, request, report_type):
        tenant = request.tenant

        if report_type == 'candidates':
            return self._export_candidates(tenant)
        elif report_type == 'applications':
            return self._export_applications(tenant)
        elif report_type == 'interviews':
            return self._export_interviews(tenant)
        else:
            return HttpResponse("Invalid report type", status=400)

    def _export_candidates(self, tenant):
        """候補者CSVエクスポート"""
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="candidates.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', '氏名', 'メール', '電話', '性別', '就業状況',
            '登録日', '登録者'
        ])

        candidates = Candidate.objects.filter(tenant=tenant).select_related('registered_by')
        for c in candidates:
            writer.writerow([
                c.id,
                c.name,
                c.email,
                c.phone or '',
                c.get_gender_display() if c.gender else '',
                c.get_employment_status_display() if c.employment_status else '',
                c.created_at.strftime('%Y-%m-%d') if c.created_at else '',
                c.registered_by.get_full_name() if c.registered_by else '',
            ])

        return response

    def _export_applications(self, tenant):
        """応募CSVエクスポート"""
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="applications.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', '候補者', '求人', 'ステータス', '応募日', '応募経路'
        ])

        applications = Application.objects.filter(
            tenant=tenant
        ).select_related('candidate', 'job', 'source')

        for a in applications:
            writer.writerow([
                a.id,
                a.candidate.name,
                a.job.title,
                a.get_status_display(),
                a.applied_at.strftime('%Y-%m-%d') if a.applied_at else '',
                a.source.name if a.source else '',
            ])

        return response

    def _export_interviews(self, tenant):
        """面接CSVエクスポート"""
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="interviews.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', '候補者', '求人', '面接官', '予定日時',
            'タイプ', 'ステータス', '結果', '評価点'
        ])

        interviews = Interview.objects.filter(
            tenant=tenant
        ).select_related('application__candidate', 'application__job', 'interviewer')

        for i in interviews:
            writer.writerow([
                i.id,
                i.candidate.name,
                i.application.job.title,
                i.interviewer.get_full_name() if i.interviewer else '',
                i.scheduled_at.strftime('%Y-%m-%d %H:%M') if i.scheduled_at else '',
                i.get_interview_type_display(),
                i.get_status_display(),
                i.get_result_display() if i.result else '',
                i.evaluation_score or '',
            ])

        return response
