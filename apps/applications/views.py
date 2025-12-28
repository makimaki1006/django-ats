"""
Django ATS - 応募ビュー
応募の一覧、詳細、作成、更新、ステータス変更
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
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
from .models import Application, ApplicationStatusChoices, ApplicationStatusHistory
from .forms import ApplicationForm, ApplicationFilterForm, ApplicationStatusForm, UnifiedApplicationForm


class ApplicationListView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    SearchMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """応募一覧"""
    model = Application
    template_name = 'applications/application_list.html'
    context_object_name = 'applications'
    search_fields = ['candidate__name', 'candidate__email', 'job__title']
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()

        # テナントでフィルタ
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)

        # ステータスフィルタ
        status = self.request.GET.get('status')
        if status and status in dict(ApplicationStatusChoices.choices):
            queryset = queryset.filter(status=status)

        # 求人フィルタ
        job_id = self.request.GET.get('job')
        if job_id:
            queryset = queryset.filter(job_id=job_id)

        # 候補者フィルタ
        candidate_id = self.request.GET.get('candidate')
        if candidate_id:
            queryset = queryset.filter(candidate_id=candidate_id)

        # アクティブのみフィルタ
        active_only = self.request.GET.get('active_only')
        if active_only == 'true':
            inactive_statuses = [
                ApplicationStatusChoices.REJECTED,
                ApplicationStatusChoices.WITHDRAWN,
                ApplicationStatusChoices.OFFER_DECLINED,
                ApplicationStatusChoices.OFFER_ACCEPTED,
            ]
            queryset = queryset.exclude(status__in=inactive_statuses)

        return queryset.select_related('candidate', 'job', 'registered_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ApplicationStatusChoices.choices
        context['filter_form'] = ApplicationFilterForm(
            self.request.GET,
            tenant=self.request.tenant
        )
        return context


class ApplicationDetailView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """応募詳細"""
    model = Application
    template_name = 'applications/application_detail.html'
    context_object_name = 'application'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset.select_related(
            'candidate', 'job', 'source', 'registered_by'
        ).prefetch_related(
            'status_history__changed_by',
            'candidate__applications__job',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ApplicationStatusChoices.choices
        context['status_form'] = ApplicationStatusForm()
        return context


class ApplicationCreateView(
    LoginRequiredMixin,
    HtmxMixin,
    CreateView
):
    """応募作成"""
    model = Application
    form_class = ApplicationForm
    template_name = 'applications/application_form.html'
    success_url = reverse_lazy('applications:application_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        # URLパラメータから初期値設定
        candidate_id = self.request.GET.get('candidate')
        job_id = self.request.GET.get('job')
        if candidate_id:
            initial['candidate'] = candidate_id
        if job_id:
            initial['job'] = job_id
        return initial

    def form_valid(self, form):
        application = form.save(commit=False)
        application.tenant = self.request.tenant
        application.registered_by = self.request.user
        application.save()

        # 初期ステータス履歴を記録
        # 新規作成時は from_status と to_status を同じにする（履歴の開始点）
        ApplicationStatusHistory.objects.create(
            tenant=self.request.tenant,
            application=application,
            from_status=application.status,
            to_status=application.status,
            changed_by=self.request.user,
            notes='新規応募登録'
        )

        messages.success(
            self.request,
            f'{application.candidate.name}さんの応募を登録しました。'
        )
        return super().form_valid(form)


class ApplicationUpdateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """応募更新"""
    model = Application
    form_class = ApplicationForm
    template_name = 'applications/application_form.html'

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
        return reverse_lazy('applications:application_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(
            self.request,
            f'{form.instance.candidate.name}さんの応募情報を更新しました。'
        )
        return super().form_valid(form)


class ApplicationStatusChangeView(
    LoginRequiredMixin,
    HtmxMixin,
    TemplateView
):
    """応募ステータス変更"""

    def post(self, request, pk, *args, **kwargs):
        queryset = Application.objects.all()
        if request.tenant:
            queryset = queryset.filter(tenant=request.tenant)

        application = get_object_or_404(queryset, pk=pk)

        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')

        if new_status and new_status in dict(ApplicationStatusChoices.choices):
            old_status = application.status
            application.change_status(new_status, user=request.user, notes=notes)

            # 内定時は内定日を記録
            if new_status == ApplicationStatusChoices.OFFER_MADE:
                application.offer_made_at = timezone.now()
                application.save()

            messages.success(
                request,
                f'{application.candidate.name}さんのステータスを「{application.get_status_display()}」に変更しました。'
            )
        else:
            messages.error(request, '無効なステータスです。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('applications:application_detail', pk=application.pk)


class ApplicationKanbanView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    TemplateView
):
    """応募カンバンボード"""
    template_name = 'applications/application_kanban.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # テナントでフィルタ
        queryset = Application.objects.all()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)

        queryset = queryset.select_related('candidate', 'job')

        # ステータス別に分類
        status_groups = {}
        for status_value, status_label in ApplicationStatusChoices.choices:
            status_groups[status_value] = {
                'label': status_label,
                'applications': queryset.filter(status=status_value)[:10]
            }

        context['status_groups'] = status_groups
        return context


class UnifiedApplicationFormView(
    LoginRequiredMixin,
    HtmxMixin,
    TemplateView
):
    """統合応募フォーム

    外部ユーザー（コンサルタント、人材紹介会社、顧客）が
    候補者情報と応募情報を一度に入力するためのフォーム。

    URL: /apply/ または /apply/{tenant_slug}/
    """
    template_name = 'applications/unified_application_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = UnifiedApplicationForm(
            tenant=self.request.tenant,
            user=self.request.user
        )
        context['tenant'] = self.request.tenant
        return context

    def post(self, request, *args, **kwargs):
        form = UnifiedApplicationForm(
            request.POST,
            tenant=request.tenant,
            user=request.user
        )

        if form.is_valid():
            candidate, application, is_new_candidate = form.save()

            # 通知を送信（将来的に実装）
            self._send_notifications(request, candidate, application, is_new_candidate)

            if is_new_candidate:
                messages.success(
                    request,
                    f'{candidate.name}さんを新規登録し、{application.job.title}への応募を受け付けました。'
                )
            else:
                messages.success(
                    request,
                    f'{candidate.name}さんの{application.job.title}への応募を受け付けました。'
                )

            # 応募完了ページにリダイレクト
            return redirect('applications:unified_complete', pk=application.pk)

        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)

    def _send_notifications(self, request, candidate, application, is_new_candidate):
        """通知を送信

        TODO: 以下の通知を実装
        - 人事担当者への通知
        - 採用コンサルタントへの通知
        """
        from apps.notifications.models import Notification
        from apps.accounts.models import UserRole

        # テナントの人事担当者とコンサルタントを取得
        recipients = request.tenant.users.filter(
            role__in=[
                UserRole.CLIENT_ADMIN,
                UserRole.CONSULTANT,
                UserRole.HIRING_MANAGER,
            ]
        )

        for recipient in recipients:
            Notification.create_notification(
                tenant=request.tenant,
                user=recipient,
                notification_type='new_application',
                title='新しい応募がありました',
                message=f'{candidate.name}さんが{application.job.title}に応募しました。',
                link=application.get_absolute_url(),
                related_object=application
            )


class UnifiedApplicationCompleteView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """統合応募フォーム完了ページ"""
    model = Application
    template_name = 'applications/unified_application_complete.html'
    context_object_name = 'application'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset.select_related('candidate', 'job')
