"""
Django ATS - 求人ビュー
求人の一覧、詳細、作成、更新、ステータス変更
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
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
from .models import Job, JobStatusChoices, EmploymentTypeChoices
from .forms import JobForm, JobFilterForm


class JobListView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    SearchMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """求人一覧"""
    model = Job
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'
    search_fields = ['title', 'unique_code', 'department', 'location']
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()

        # テナントでフィルタ
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)

        # ステータスフィルタ
        status = self.request.GET.get('status')
        if status and status in dict(JobStatusChoices.choices):
            queryset = queryset.filter(status=status)

        # 雇用形態フィルタ
        employment_type = self.request.GET.get('employment_type')
        if employment_type and employment_type in dict(EmploymentTypeChoices.choices):
            queryset = queryset.filter(employment_type=employment_type)

        return queryset.select_related('hiring_manager', 'created_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = JobStatusChoices.choices
        context['employment_type_choices'] = EmploymentTypeChoices.choices
        context['filter_form'] = JobFilterForm(self.request.GET)
        return context


class JobDetailView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """求人詳細"""
    model = Job
    template_name = 'jobs/job_detail.html'
    context_object_name = 'job'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset.select_related(
            'hiring_manager', 'created_by'
        ).prefetch_related(
            'applications__candidate',
            'personas',
            'agent_companies'
        )


class JobCreateView(
    LoginRequiredMixin,
    HtmxMixin,
    CreateView
):
    """求人作成"""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'
    success_url = reverse_lazy('jobs:job_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        job = form.save(commit=False)
        job.tenant = self.request.tenant
        job.created_by = self.request.user
        job.save()
        messages.success(self.request, f'求人「{job.title}」を作成しました。')
        return super().form_valid(form)


class JobUpdateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """求人更新"""
    model = Job
    form_class = JobForm
    template_name = 'jobs/job_form.html'

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
        return reverse_lazy('jobs:job_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'求人「{form.instance.title}」を更新しました。')
        return super().form_valid(form)


class JobStatusChangeView(
    LoginRequiredMixin,
    HtmxMixin,
    TemplateView
):
    """求人ステータス変更"""

    def post(self, request, pk, action, *args, **kwargs):
        queryset = Job.objects.all()
        if request.tenant:
            queryset = queryset.filter(tenant=request.tenant)

        job = get_object_or_404(queryset, pk=pk)

        if action == 'publish':
            job.publish()
            messages.success(request, f'求人「{job.title}」を公開しました。')
        elif action == 'pause':
            job.pause()
            messages.success(request, f'求人「{job.title}」を一時停止しました。')
        elif action == 'close':
            job.close()
            messages.success(request, f'求人「{job.title}」を終了しました。')
        else:
            messages.error(request, '無効なアクションです。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('jobs:job_detail', pk=job.pk)


class JobDuplicateView(
    LoginRequiredMixin,
    HtmxMixin,
    TemplateView
):
    """求人複製"""

    def post(self, request, pk, *args, **kwargs):
        queryset = Job.objects.all()
        if request.tenant:
            queryset = queryset.filter(tenant=request.tenant)

        job = get_object_or_404(queryset, pk=pk)

        # 新しいコードを生成
        base_code = job.unique_code
        counter = 1
        new_code = f"{base_code}_copy{counter}"
        while Job.objects.filter(tenant=request.tenant, unique_code=new_code).exists():
            counter += 1
            new_code = f"{base_code}_copy{counter}"

        new_job = job.duplicate(new_code=new_code)
        messages.success(request, f'求人「{job.title}」を複製しました。')

        return redirect('jobs:job_update', pk=new_job.pk)
