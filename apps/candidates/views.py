"""
Django ATS - 候補者ビュー
候補者の一覧、詳細、作成、更新、アーカイブ、CSVインポート、コメント
"""

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    TemplateView,
    View,
)

from apps.core.mixins import (
    HtmxMixin,
    TenantQuerysetMixin,
    PaginationMixin,
    SearchMixin,
    LimitedCandidateAccessMixin,
    FullCandidateAccessMixin,
    CandidateQuerysetFilterMixin,
)
from .models import Candidate, CandidateComment, ImportHistory, GenderChoices, EmploymentStatusChoices
from .forms import CandidateForm, CandidateFilterForm, CSVImportForm, CommentForm
from .services import CandidateCSVImporter


class CandidateListView(
    LimitedCandidateAccessMixin,
    CandidateQuerysetFilterMixin,
    SearchMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """候補者一覧

    アクセス権限:
    - フルアクセス: system_admin, consultant, client_admin, hiring_manager
    - 限定アクセス: client_recruiter, interviewer, agent（担当分のみ）
    """
    model = Candidate
    template_name = 'candidates/candidate_list.html'
    context_object_name = 'candidates'
    search_fields = ['name', 'name_kana', 'email', 'current_company']
    paginate_by = 20

    def get_queryset(self):
        # ロールベースのフィルタリングを適用
        queryset = super().get_queryset()

        # アーカイブ除外（デフォルト）
        if not self.request.GET.get('include_archived'):
            queryset = queryset.filter(is_archived=False)

        # 就業状況フィルタ
        status = self.request.GET.get('employment_status')
        if status and status in dict(EmploymentStatusChoices.choices):
            queryset = queryset.filter(employment_status=status)

        # 性別フィルタ
        gender = self.request.GET.get('gender')
        if gender and gender in dict(GenderChoices.choices):
            queryset = queryset.filter(gender=gender)

        # エージェント経由のみ
        if self.request.GET.get('agent_only'):
            queryset = queryset.filter(agent_company__isnull=False)

        return queryset.select_related('agent_company', 'registered_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employment_status_choices'] = EmploymentStatusChoices.choices
        context['gender_choices'] = GenderChoices.choices
        context['filter_form'] = CandidateFilterForm(self.request.GET)
        return context


class CandidateDetailView(
    LimitedCandidateAccessMixin,
    CandidateQuerysetFilterMixin,
    HtmxMixin,
    DetailView
):
    """候補者詳細

    アクセス権限:
    - フルアクセス: 全情報を表示
    - 限定アクセス: 担当候補者のみ表示（面接官・エージェント）
    """
    model = Candidate
    template_name = 'candidates/candidate_detail.html'
    context_object_name = 'candidate'

    def get_queryset(self):
        # ロールベースのフィルタリングを適用
        queryset = super().get_queryset()
        return queryset.select_related(
            'agent_company', 'registered_by', 'source'
        ).prefetch_related('applications__job')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # アクティブなコメント（論理削除されていない）を取得
        context['comments'] = self.object.comments.filter(
            is_deleted=False
        ).select_related('author').order_by('-created_at')
        context['comment_form'] = CommentForm()
        # ユーザーのアクセスレベルをコンテキストに追加
        context['has_full_access'] = getattr(self.request.user, 'has_full_candidate_access', False)
        return context


class CandidateCreateView(
    FullCandidateAccessMixin,
    HtmxMixin,
    CreateView
):
    """候補者作成

    アクセス権限:
    - フルアクセス権限が必要（system_admin, consultant, client_admin, hiring_manager）
    """
    model = Candidate
    form_class = CandidateForm
    template_name = 'candidates/candidate_form.html'
    success_url = reverse_lazy('candidates:candidate_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        candidate = form.save(commit=False)
        candidate.tenant = self.request.tenant
        candidate.registered_by = self.request.user
        candidate.save()
        messages.success(self.request, f'候補者「{candidate.name}」を登録しました。')
        return super().form_valid(form)


class CandidateUpdateView(
    FullCandidateAccessMixin,
    CandidateQuerysetFilterMixin,
    HtmxMixin,
    UpdateView
):
    """候補者更新

    アクセス権限:
    - フルアクセス権限が必要（system_admin, consultant, client_admin, hiring_manager）
    """
    model = Candidate
    form_class = CandidateForm
    template_name = 'candidates/candidate_form.html'

    def get_queryset(self):
        # ロールベースのフィルタリングを適用
        return super().get_queryset()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_success_url(self):
        return reverse_lazy('candidates:candidate_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'候補者「{form.instance.name}」を更新しました。')
        return super().form_valid(form)


class CandidateArchiveView(
    FullCandidateAccessMixin,
    HtmxMixin,
    TemplateView
):
    """候補者アーカイブ/復元

    アクセス権限:
    - フルアクセス権限が必要（system_admin, consultant, client_admin, hiring_manager）
    """

    def post(self, request, pk, *args, **kwargs):
        # ロールベースのフィルタリングを適用
        queryset = Candidate.objects.for_user(request.user)

        candidate = get_object_or_404(queryset, pk=pk)
        candidate.is_archived = not candidate.is_archived
        candidate.save(update_fields=['is_archived', 'updated_at'])

        action = 'アーカイブ' if candidate.is_archived else '復元'
        messages.success(request, f'候補者「{candidate.name}」を{action}しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})
        return redirect('candidates:candidate_list')


class CandidateQuickSearchView(
    LimitedCandidateAccessMixin,
    CandidateQuerysetFilterMixin,
    HtmxMixin,
    ListView
):
    """候補者クイック検索（htmx用）

    アクセス権限:
    - フルアクセス: 全候補者を検索可能
    - 限定アクセス: 担当候補者のみ検索可能
    """
    model = Candidate
    template_name = 'candidates/partials/candidate_search_results.html'
    context_object_name = 'candidates'

    def get_queryset(self):
        # ロールベースのフィルタリングを適用
        queryset = super().get_queryset()

        query = self.request.GET.get('q', '')
        if query and len(query) >= 2:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(name_kana__icontains=query) |
                Q(email__icontains=query)
            )[:10]
        else:
            queryset = queryset.none()

        return queryset


# =============================================================================
# CSVインポート関連ビュー
# =============================================================================

class CSVImportView(
    FullCandidateAccessMixin,
    HtmxMixin,
    TemplateView
):
    """CSVインポートフォーム

    アクセス権限:
    - フルアクセス権限が必要（system_admin, consultant, client_admin, hiring_manager）
    """
    template_name = 'candidates/csv_import.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CSVImportForm()
        # 最近のインポート履歴
        context['recent_imports'] = ImportHistory.objects.filter(
            tenant=self.request.tenant
        ).order_by('-created_at')[:5]
        return context

    def post(self, request, *args, **kwargs):
        form = CSVImportForm(request.POST, request.FILES)

        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            skip_duplicates = form.cleaned_data['skip_duplicates']

            importer = CandidateCSVImporter(
                tenant=request.tenant,
                user=request.user
            )

            try:
                history = importer.import_csv(
                    csv_file=csv_file,
                    skip_duplicates=skip_duplicates
                )

                if history.status == ImportHistory.StatusChoices.COMPLETED:
                    messages.success(
                        request,
                        f'{history.success_count}件の候補者をインポートしました。'
                    )
                elif history.status == ImportHistory.StatusChoices.PARTIAL:
                    messages.warning(
                        request,
                        f'{history.success_count}件をインポート、{history.error_count}件でエラーが発生しました。'
                    )
                else:
                    messages.error(
                        request,
                        'インポートに失敗しました。エラー詳細を確認してください。'
                    )

                return redirect('candidates:csv_import_result', pk=history.pk)

            except Exception as e:
                messages.error(request, f'インポート中にエラーが発生しました: {str(e)}')

        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)


class CSVImportResultView(
    FullCandidateAccessMixin,
    TenantQuerysetMixin,
    HtmxMixin,
    DetailView
):
    """CSVインポート結果表示

    アクセス権限:
    - フルアクセス権限が必要（system_admin, consultant, client_admin, hiring_manager）
    """
    model = ImportHistory
    template_name = 'candidates/csv_import_result.html'
    context_object_name = 'import_history'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset


class CSVTemplateDownloadView(
    FullCandidateAccessMixin,
    View
):
    """CSVテンプレートダウンロード

    アクセス権限:
    - フルアクセス権限が必要（system_admin, consultant, client_admin, hiring_manager）
    """

    def get(self, request, *args, **kwargs):
        csv_content = CandidateCSVImporter.generate_template_csv()

        response = HttpResponse(
            csv_content,
            content_type='text/csv; charset=utf-8-sig'
        )
        response['Content-Disposition'] = 'attachment; filename="candidate_import_template.csv"'
        return response


class CSVImportHistoryView(
    FullCandidateAccessMixin,
    TenantQuerysetMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """CSVインポート履歴一覧

    アクセス権限:
    - フルアクセス権限が必要（system_admin, consultant, client_admin, hiring_manager）
    """
    model = ImportHistory
    template_name = 'candidates/csv_import_history.html'
    context_object_name = 'import_histories'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.tenant:
            queryset = queryset.filter(tenant=self.request.tenant)
        return queryset.order_by('-created_at')


# =============================================================================
# コメント関連ビュー
# =============================================================================

class CandidateCommentCreateView(
    LimitedCandidateAccessMixin,
    HtmxMixin,
    View
):
    """候補者コメント作成

    アクセス権限:
    - 候補者閲覧権限があればコメント可能
    """

    def post(self, request, candidate_pk, *args, **kwargs):
        # ロールベースのフィルタリングを適用
        queryset = Candidate.objects.for_user(request.user)
        candidate = get_object_or_404(queryset, pk=candidate_pk)

        form = CommentForm(request.POST)
        if form.is_valid():
            comment = CandidateComment.objects.create(
                tenant=request.tenant,
                candidate=candidate,
                author=request.user,
                content=form.cleaned_data['content']
            )
            messages.success(request, 'コメントを投稿しました。')

            if request.htmx:
                # htmxの場合はコメント部分のみ再描画
                return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

        return redirect('candidates:candidate_detail', pk=candidate.pk)


class CandidateCommentUpdateView(
    LimitedCandidateAccessMixin,
    HtmxMixin,
    View
):
    """候補者コメント編集

    アクセス権限:
    - 自分が投稿したコメントのみ編集可能
    """

    def post(self, request, candidate_pk, comment_pk, *args, **kwargs):
        # コメント取得（自分のコメントのみ編集可能）
        comment = get_object_or_404(
            CandidateComment,
            pk=comment_pk,
            candidate__pk=candidate_pk,
            tenant=request.tenant,
            author=request.user,
            is_deleted=False
        )

        form = CommentForm(request.POST)
        if form.is_valid():
            comment.edit(
                new_content=form.cleaned_data['content'],
                editor=request.user
            )
            messages.success(request, 'コメントを編集しました。')

            if request.htmx:
                return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

        return redirect('candidates:candidate_detail', pk=candidate_pk)


class CandidateCommentDeleteView(
    LimitedCandidateAccessMixin,
    HtmxMixin,
    View
):
    """候補者コメント削除（論理削除）

    アクセス権限:
    - 自分が投稿したコメントのみ削除可能
    """

    def post(self, request, candidate_pk, comment_pk, *args, **kwargs):
        # コメント取得（自分のコメントのみ削除可能）
        comment = get_object_or_404(
            CandidateComment,
            pk=comment_pk,
            candidate__pk=candidate_pk,
            tenant=request.tenant,
            author=request.user,
            is_deleted=False
        )

        comment.soft_delete(request.user)
        messages.success(request, 'コメントを削除しました。')

        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

        return redirect('candidates:candidate_detail', pk=candidate_pk)
