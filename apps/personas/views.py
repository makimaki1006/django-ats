"""
Django ATS - ペルソナビュー
ペルソナの一覧、詳細、作成、更新、削除、複製
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    View,
)

from apps.core.mixins import (
    HtmxMixin,
    TenantQuerysetMixin,
    PaginationMixin,
    SearchMixin,
)
from .models import Persona
from .forms import PersonaForm, PersonaFilterForm


class PersonaListView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    SearchMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """ペルソナ一覧"""
    model = Persona
    template_name = 'personas/persona_list.html'
    context_object_name = 'personas'
    search_fields = ['name', 'description', 'work_style', 'motivation']
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()

        # 有効フィルタ
        is_active = self.request.GET.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)

        # テンプレートフィルタ
        is_template = self.request.GET.get('is_template')
        if is_template == 'true':
            queryset = queryset.filter(is_template=True)
        elif is_template == 'false':
            queryset = queryset.filter(is_template=False)

        # 学歴フィルタ
        education_level = self.request.GET.get('education_level')
        if education_level and education_level in dict(Persona.EducationLevelChoices.choices):
            queryset = queryset.filter(education_level=education_level)

        return queryset.select_related('created_by').annotate(
            job_count=Count('persona_jobs')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PersonaFilterForm(self.request.GET)
        context['education_level_choices'] = Persona.EducationLevelChoices.choices
        return context


class PersonaDetailView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """ペルソナ詳細"""
    model = Persona
    template_name = 'personas/persona_detail.html'
    context_object_name = 'persona'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('created_by').prefetch_related(
            'persona_jobs__job'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 関連する求人を取得
        context['linked_jobs'] = [
            jp.job for jp in self.object.persona_jobs.select_related('job').all()
        ]
        return context


class PersonaCreateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    CreateView
):
    """ペルソナ作成"""
    model = Persona
    form_class = PersonaForm
    template_name = 'personas/persona_form.html'
    success_url = reverse_lazy('personas:persona_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        persona = form.save(commit=False)
        persona.tenant = self.request.tenant
        persona.created_by = self.request.user
        persona.save()
        messages.success(self.request, f'ペルソナ「{persona.name}」を作成しました。')
        return super().form_valid(form)


class PersonaUpdateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    UpdateView
):
    """ペルソナ更新"""
    model = Persona
    form_class = PersonaForm
    template_name = 'personas/persona_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_success_url(self):
        return reverse_lazy('personas:persona_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'ペルソナ「{form.instance.name}」を更新しました。')
        return super().form_valid(form)


class PersonaDeleteView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    View
):
    """ペルソナ削除"""

    def post(self, request, pk, *args, **kwargs):
        queryset = Persona.objects.filter(tenant=request.tenant)
        persona = get_object_or_404(queryset, pk=pk)

        # 関連する求人があれば削除不可
        if persona.persona_jobs.exists():
            messages.error(
                request,
                f'ペルソナ「{persona.name}」は求人に紐付いているため削除できません。'
            )
            if request.htmx:
                return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
            return redirect('personas:persona_list')

        name = persona.name
        persona.delete()
        messages.success(request, f'ペルソナ「{name}」を削除しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('personas:persona_list')


class PersonaDuplicateView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    View
):
    """ペルソナ複製"""

    def post(self, request, pk, *args, **kwargs):
        queryset = Persona.objects.filter(tenant=request.tenant)
        persona = get_object_or_404(queryset, pk=pk)

        # 複製を作成
        new_persona = persona.duplicate()
        new_persona.created_by = request.user
        new_persona.save()

        messages.success(
            request,
            f'ペルソナ「{persona.name}」を複製しました。'
        )

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('personas:persona_detail', pk=new_persona.pk)


class PersonaToggleActiveView(
    LoginRequiredMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    View
):
    """ペルソナ有効/無効切り替え"""

    def post(self, request, pk, *args, **kwargs):
        queryset = Persona.objects.filter(tenant=request.tenant)
        persona = get_object_or_404(queryset, pk=pk)

        persona.is_active = not persona.is_active
        persona.save(update_fields=['is_active', 'updated_at'])

        status = '有効' if persona.is_active else '無効'
        messages.success(request, f'ペルソナ「{persona.name}」を{status}にしました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('personas:persona_list')
