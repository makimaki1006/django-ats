"""
Django ATS - 面接ビュー
面接の一覧、詳細、作成、更新、面接サポート
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    TemplateView,
)

from apps.core.mixins import (
    HtmxMixin,
    TenantQuerysetMixin,
    PaginationMixin,
    SearchMixin,
)
from .models import (
    Interview,
    InterviewTypeChoices,
    InterviewStatusChoices,
    InterviewResultChoices,
)
from .forms import InterviewForm, InterviewFilterForm, InterviewResultForm


class InterviewListView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    SearchMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """面接一覧"""
    model = Interview
    template_name = 'interviews/interview_list.html'
    context_object_name = 'interviews'
    search_fields = ['application__candidate__name', 'application__job__title']
    paginate_by = 20

    def get_template_names(self):
        """HTMXリクエストの場合はパーシャルテンプレートを返す"""
        if self.request.htmx:
            return ['interviews/partials/interview_table.html']
        return [self.template_name]

    def get_queryset(self):
        queryset = super().get_queryset()

        # テナントでフィルタ
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)

        # ステータスフィルタ
        status = self.request.GET.get('status')
        if status and status in dict(InterviewStatusChoices.choices):
            queryset = queryset.filter(status=status)

        # 日付フィルタ
        date_filter = self.request.GET.get('date_filter')
        today = timezone.now().date()
        if date_filter == 'today':
            queryset = queryset.filter(scheduled_at__date=today)
        elif date_filter == 'week':
            from datetime import timedelta
            week_end = today + timedelta(days=7)
            queryset = queryset.filter(
                scheduled_at__date__gte=today,
                scheduled_at__date__lte=week_end
            )
        elif date_filter == 'upcoming':
            queryset = queryset.filter(
                scheduled_at__gte=timezone.now(),
                status__in=[InterviewStatusChoices.SCHEDULED, InterviewStatusChoices.CONFIRMED]
            )

        return queryset.select_related(
            'application__candidate',
            'application__job',
            'interviewer'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = InterviewStatusChoices.choices
        context['filter_form'] = InterviewFilterForm(self.request.GET)
        # Empty Stateで使用する作成URL
        context['create_url'] = reverse_lazy('interviews:interview_create')

        # 今日の面接数
        today = timezone.now().date()
        if self.request.tenant:
            context['today_count'] = Interview.objects.filter(
                tenant=self.request.tenant,
                scheduled_at__date=today
            ).count()

        return context


class InterviewDetailView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """面接詳細"""
    model = Interview
    template_name = 'interviews/interview_detail.html'
    context_object_name = 'interview'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset.select_related(
            'application__candidate',
            'application__job',
            'interviewer'
        ).prefetch_related(
            'additional_interviewers',
            'feedback_requests__requested_to'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['result_form'] = InterviewResultForm()
        context['result_choices'] = InterviewResultChoices.choices
        return context


class InterviewCreateView(
    LoginRequiredMixin,
    HtmxMixin,
    CreateView
):
    """面接作成"""
    model = Interview
    form_class = InterviewForm
    template_name = 'interviews/interview_form.html'
    success_url = reverse_lazy('interviews:interview_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        application_id = self.request.GET.get('application')
        if application_id:
            initial['application'] = application_id
        return initial

    def form_valid(self, form):
        interview = form.save(commit=False)
        interview.tenant = self.request.tenant
        interview.save()
        form.save_m2m()

        messages.success(
            self.request,
            f'{interview.candidate.name}さんの面接を登録しました。'
        )
        return super().form_valid(form)


class InterviewUpdateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """面接更新"""
    model = Interview
    form_class = InterviewForm
    template_name = 'interviews/interview_form.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_success_url(self):
        return reverse_lazy('interviews:interview_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(
            self.request,
            f'{form.instance.candidate.name}さんの面接情報を更新しました。'
        )
        return super().form_valid(form)


class InterviewResultView(
    LoginRequiredMixin,
    HtmxMixin,
    TemplateView
):
    """面接結果入力"""

    def post(self, request, pk, *args, **kwargs):
        queryset = Interview.objects.all()
        if request.tenant:
            queryset = queryset.filter(tenant=request.tenant)

        interview = get_object_or_404(queryset, pk=pk)

        result = request.POST.get('result')
        score = request.POST.get('evaluation_score')
        feedback = request.POST.get('feedback', '')
        internal_notes = request.POST.get('internal_notes', '')

        if result and result in dict(InterviewResultChoices.choices):
            interview.complete(
                result=result,
                score=int(score) if score else None,
                feedback=feedback,
                internal_notes=internal_notes
            )

            messages.success(
                request,
                f'{interview.candidate.name}さんの面接結果を登録しました。'
            )
        else:
            messages.error(request, '無効な結果です。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('interviews:interview_detail', pk=interview.pk)


class InterviewCancelView(
    LoginRequiredMixin,
    HtmxMixin,
    TemplateView
):
    """面接キャンセル"""

    def post(self, request, pk, *args, **kwargs):
        queryset = Interview.objects.all()
        if request.tenant:
            queryset = queryset.filter(tenant=request.tenant)

        interview = get_object_or_404(queryset, pk=pk)
        reason = request.POST.get('reason', '')
        interview.cancel(reason)

        messages.success(
            request,
            f'{interview.candidate.name}さんの面接をキャンセルしました。'
        )

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('interviews:interview_list')


class InterviewCalendarView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    TemplateView
):
    """面接カレンダー"""
    template_name = 'interviews/interview_calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 今週の面接を取得
        today = timezone.now().date()
        from datetime import timedelta
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        queryset = Interview.objects.all()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)

        context['interviews'] = queryset.filter(
            scheduled_at__date__gte=week_start,
            scheduled_at__date__lte=week_end
        ).select_related(
            'application__candidate',
            'application__job'
        ).order_by('scheduled_at')

        context['week_start'] = week_start
        context['week_end'] = week_end

        return context


# =============================================================================
# 面接サポート画面
# =============================================================================

class InterviewSupportDashboardView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    TemplateView
):
    """面接サポートダッシュボード

    面接官向けのダッシュボード。
    自分が担当する面接の一覧と、必要な情報をまとめて表示。
    """
    template_name = 'interviews/interview_support_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()
        from datetime import timedelta

        # 自分が担当する面接（メイン面接官または同席者）
        base_queryset = Interview.objects.filter(tenant=self.request.tenant)

        # 今日の面接
        today_interviews = base_queryset.filter(
            scheduled_at__date=today
        ).filter(
            models.Q(interviewer=user) | models.Q(additional_interviewers=user)
        ).select_related(
            'application__candidate',
            'application__job'
        ).prefetch_related(
            'additional_interviewers'
        ).order_by('scheduled_at').distinct()

        context['today_interviews'] = today_interviews

        # 今週の残りの面接（今日を除く）
        week_end = today + timedelta(days=7)
        upcoming_interviews = base_queryset.filter(
            scheduled_at__date__gt=today,
            scheduled_at__date__lte=week_end,
            status__in=[InterviewStatusChoices.SCHEDULED, InterviewStatusChoices.CONFIRMED]
        ).filter(
            models.Q(interviewer=user) | models.Q(additional_interviewers=user)
        ).select_related(
            'application__candidate',
            'application__job'
        ).order_by('scheduled_at').distinct()

        context['upcoming_interviews'] = upcoming_interviews

        # 評価待ちの面接（完了したが結果未入力）
        pending_evaluation = base_queryset.filter(
            status=InterviewStatusChoices.COMPLETED,
            result=InterviewResultChoices.PENDING
        ).filter(
            models.Q(interviewer=user) | models.Q(additional_interviewers=user)
        ).select_related(
            'application__candidate',
            'application__job'
        ).order_by('-scheduled_at').distinct()

        context['pending_evaluation'] = pending_evaluation

        # 統計情報
        context['today_count'] = today_interviews.count()
        context['upcoming_count'] = upcoming_interviews.count()
        context['pending_count'] = pending_evaluation.count()

        return context


class InterviewSupportDetailView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """面接サポート詳細

    面接官が面接前に確認する情報をまとめた画面。
    - 候補者情報
    - 求人情報
    - 過去の面接履歴
    - 応募履歴
    - 評価入力フォーム
    """
    model = Interview
    template_name = 'interviews/interview_support_detail.html'
    context_object_name = 'interview'

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)

        # 自分が担当する面接のみ
        from django.db.models import Q
        queryset = queryset.filter(
            Q(interviewer=user) | Q(additional_interviewers=user)
        )

        return queryset.select_related(
            'application__candidate',
            'application__candidate__agent_company',
            'application__job',
            'interviewer'
        ).prefetch_related(
            'additional_interviewers',
            'feedback_requests__requested_to'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interview = self.object
        candidate = interview.candidate
        application = interview.application

        # 候補者の過去の面接（この面接以外）
        context['past_interviews'] = Interview.objects.filter(
            tenant=self.request.tenant,
            application__candidate=candidate,
            status=InterviewStatusChoices.COMPLETED
        ).exclude(
            pk=interview.pk
        ).select_related(
            'application__job',
            'interviewer'
        ).order_by('-scheduled_at')[:5]

        # 候補者の他の応募
        context['other_applications'] = candidate.applications.filter(
            tenant=self.request.tenant
        ).exclude(
            pk=application.pk
        ).select_related('job')[:5]

        # 評価フォーム
        context['result_form'] = InterviewResultForm()
        context['result_choices'] = InterviewResultChoices.choices

        # 面接タイプ・ステータス選択肢
        context['type_choices'] = InterviewTypeChoices.choices
        context['status_choices'] = InterviewStatusChoices.choices

        # ユーザーがメイン面接官かどうか
        context['is_main_interviewer'] = interview.interviewer == self.request.user

        return context


class InterviewQuickEvaluationView(
    LoginRequiredMixin,
    HtmxMixin,
    TemplateView
):
    """クイック評価入力

    面接サポート画面からの評価入力。
    htmxでモーダル表示。
    """

    def post(self, request, pk, *args, **kwargs):
        from django.db.models import Q

        queryset = Interview.objects.filter(tenant=request.tenant).filter(
            Q(interviewer=request.user) | Q(additional_interviewers=request.user)
        )

        interview = get_object_or_404(queryset, pk=pk)

        result = request.POST.get('result')
        score = request.POST.get('evaluation_score')
        feedback = request.POST.get('feedback', '')
        internal_notes = request.POST.get('internal_notes', '')

        if result and result in dict(InterviewResultChoices.choices):
            interview.complete(
                result=result,
                score=int(score) if score else None,
                feedback=feedback,
                internal_notes=internal_notes
            )

            messages.success(
                request,
                f'{interview.candidate.name}さんの面接評価を登録しました。'
            )
        else:
            messages.error(request, '無効な結果です。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('interviews:interview_support_detail', pk=interview.pk)
