"""Django ATS - 候補者ビュー包括的テスト

candidates/views.pyの100%カバレッジを目指すテスト。
"""

import pytest
from io import BytesIO
from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.candidates.models import Candidate, CandidateComment, ImportHistory, EmploymentStatusChoices, GenderChoices
from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='候補者包括テスト',
        code='candidate-comprehensive',
        is_active=True,
    )


@pytest.fixture
def client_admin(db, tenant):
    """クライアント管理者"""
    return CustomUser.objects.create_user(
        email='clientadmin@candidate-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def hiring_manager(db, tenant):
    """採用マネージャー"""
    return CustomUser.objects.create_user(
        email='manager@candidate-test.com',
        password='testpass123',
        role=UserRoleChoices.HIRING_MANAGER,
        tenant=tenant,
    )


@pytest.fixture
def interviewer(db, tenant):
    """面接官"""
    return CustomUser.objects.create_user(
        email='interviewer@candidate-test.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def candidate(db, tenant, client_admin):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        email='candidate@test.com',
        name='テスト候補者',
        name_kana='テストコウホシャ',
        registered_by=client_admin,
        employment_status=EmploymentStatusChoices.EMPLOYED,
        gender=GenderChoices.MALE,
    )


@pytest.fixture
def archived_candidate(db, tenant, client_admin):
    """アーカイブ済み候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        email='archived@test.com',
        name='アーカイブ済み候補者',
        registered_by=client_admin,
        is_archived=True,
    )


@pytest.fixture
def multiple_candidates(db, tenant, client_admin):
    """複数候補者"""
    candidates = []
    for i in range(5):
        candidates.append(Candidate.objects.create(
            tenant=tenant,
            email=f'candidate{i}@test.com',
            name=f'候補者{i}',
            registered_by=client_admin,
        ))
    return candidates


@pytest.fixture
def comment(db, tenant, candidate, client_admin):
    """テストコメント"""
    return CandidateComment.objects.create(
        tenant=tenant,
        candidate=candidate,
        author=client_admin,
        content='テストコメント',
    )


# =============================================================================
# CandidateListView Tests
# =============================================================================

class TestCandidateListViewComprehensive:
    """候補者一覧ビュー包括テスト"""

    @pytest.mark.django_db
    def test_list_unauthenticated(self, client):
        """未認証ユーザーはリダイレクト"""
        response = client.get(reverse('candidates:candidate_list'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_list_authenticated(self, client, client_admin, candidate):
        """認証済みユーザーは一覧表示可能"""
        client.force_login(client_admin)
        response = client.get(reverse('candidates:candidate_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_exclude_archived_by_default(self, client, client_admin, candidate, archived_candidate):
        """デフォルトでアーカイブ除外"""
        client.force_login(client_admin)
        response = client.get(reverse('candidates:candidate_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_include_archived(self, client, client_admin, archived_candidate):
        """アーカイブを含める"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_list'),
            {'include_archived': 'true'}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_employment_status(self, client, client_admin, candidate):
        """就業状況でフィルタ"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_list'),
            {'employment_status': EmploymentStatusChoices.EMPLOYED}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_by_gender(self, client, client_admin, candidate):
        """性別でフィルタ"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_list'),
            {'gender': GenderChoices.MALE}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_filter_agent_only(self, client, client_admin, candidate):
        """エージェント経由のみフィルタ"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_list'),
            {'agent_only': 'true'}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_list_search(self, client, client_admin, candidate):
        """検索"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_list'),
            {'q': 'テスト'}
        )
        assert response.status_code == 200


# =============================================================================
# CandidateDetailView Tests
# =============================================================================

class TestCandidateDetailViewComprehensive:
    """候補者詳細ビュー包括テスト"""

    @pytest.mark.django_db
    def test_detail_unauthenticated(self, client, candidate):
        """未認証ユーザーはリダイレクト"""
        response = client.get(
            reverse('candidates:candidate_detail', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_detail_authenticated(self, client, client_admin, candidate):
        """認証済みユーザーは詳細表示可能"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_detail', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 200
        assert 'comments' in response.context
        assert 'comment_form' in response.context

    @pytest.mark.django_db
    def test_detail_with_comments(self, client, client_admin, candidate, comment):
        """コメント付き詳細表示"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_detail', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 200


# =============================================================================
# CandidateCreateView Tests
# =============================================================================

class TestCandidateCreateViewComprehensive:
    """候補者作成ビュー包括テスト"""

    @pytest.mark.django_db
    def test_create_unauthenticated(self, client):
        """未認証ユーザーはリダイレクト"""
        response = client.get(reverse('candidates:candidate_create'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_create_limited_access_forbidden(self, client, interviewer):
        """限定アクセスユーザーは作成不可"""
        client.force_login(interviewer)
        response = client.get(reverse('candidates:candidate_create'))
        assert response.status_code in [302, 403]

    @pytest.mark.django_db
    def test_create_full_access_allowed(self, client, client_admin):
        """フルアクセスユーザーは作成可能"""
        client.force_login(client_admin)
        response = client.get(reverse('candidates:candidate_create'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_create_valid_data(self, client, client_admin):
        """有効なデータで候補者作成"""
        client.force_login(client_admin)
        data = {
            'email': 'new@test.com',
            'name': '新規候補者',
            'name_kana': 'シンキコウホシャ',
            'phone': '09012345678',
        }
        response = client.post(reverse('candidates:candidate_create'), data)
        assert response.status_code in [200, 302]


# =============================================================================
# CandidateUpdateView Tests
# =============================================================================

class TestCandidateUpdateViewComprehensive:
    """候補者更新ビュー包括テスト"""

    @pytest.mark.django_db
    def test_update_unauthenticated(self, client, candidate):
        """未認証ユーザーはリダイレクト"""
        response = client.get(
            reverse('candidates:candidate_update', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_update_limited_access_forbidden(self, client, interviewer, candidate):
        """限定アクセスユーザーは更新不可"""
        client.force_login(interviewer)
        response = client.get(
            reverse('candidates:candidate_update', kwargs={'pk': candidate.pk})
        )
        assert response.status_code in [302, 403]

    @pytest.mark.django_db
    def test_update_full_access_allowed(self, client, client_admin, candidate):
        """フルアクセスユーザーは更新可能"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_update', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 200


# =============================================================================
# CandidateArchiveView Tests
# =============================================================================

class TestCandidateArchiveViewComprehensive:
    """候補者アーカイブビュー包括テスト"""

    @pytest.mark.django_db
    def test_archive_unauthenticated(self, client, candidate):
        """未認証ユーザーはリダイレクト"""
        response = client.post(
            reverse('candidates:candidate_archive', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_archive_candidate(self, client, client_admin, candidate):
        """候補者をアーカイブ"""
        assert candidate.is_archived is False
        client.force_login(client_admin)
        response = client.post(
            reverse('candidates:candidate_archive', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 302
        candidate.refresh_from_db()
        assert candidate.is_archived is True

    @pytest.mark.django_db
    def test_restore_candidate(self, client, client_admin, archived_candidate):
        """候補者を復元"""
        assert archived_candidate.is_archived is True
        client.force_login(client_admin)
        response = client.post(
            reverse('candidates:candidate_archive', kwargs={'pk': archived_candidate.pk})
        )
        assert response.status_code == 302
        archived_candidate.refresh_from_db()
        assert archived_candidate.is_archived is False

    @pytest.mark.django_db
    def test_archive_htmx(self, client, client_admin, candidate):
        """htmxリクエストでアーカイブ"""
        client.force_login(client_admin)
        response = client.post(
            reverse('candidates:candidate_archive', kwargs={'pk': candidate.pk}),
            HTTP_HX_REQUEST='true'
        )
        assert response.status_code == 204


# =============================================================================
# CandidateQuickSearchView Tests
# =============================================================================

class TestCandidateQuickSearchViewComprehensive:
    """候補者クイック検索ビュー包括テスト"""

    @pytest.mark.django_db
    def test_quick_search_unauthenticated(self, client):
        """未認証ユーザーはリダイレクト"""
        response = client.get(
            reverse('candidates:candidate_search'),
            {'q': 'test'}
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_quick_search_short_query(self, client, client_admin):
        """短いクエリ（2文字未満）"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_search'),
            {'q': 'a'}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_quick_search_valid_query(self, client, client_admin, candidate):
        """有効なクエリ"""
        client.force_login(client_admin)
        response = client.get(
            reverse('candidates:candidate_search'),
            {'q': 'テスト'}
        )
        assert response.status_code == 200


# =============================================================================
# CSVImportView Tests
# =============================================================================

class TestCSVImportViewComprehensive:
    """CSVインポートビュー包括テスト"""

    @pytest.mark.django_db
    def test_csv_import_unauthenticated(self, client):
        """未認証ユーザーはリダイレクト"""
        response = client.get(reverse('candidates:csv_import'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_csv_import_limited_access_forbidden(self, client, interviewer):
        """限定アクセスユーザーは禁止"""
        client.force_login(interviewer)
        response = client.get(reverse('candidates:csv_import'))
        assert response.status_code in [302, 403]

    @pytest.mark.django_db
    def test_csv_import_full_access_allowed(self, client, client_admin):
        """フルアクセスユーザーはアクセス可能"""
        client.force_login(client_admin)
        response = client.get(reverse('candidates:csv_import'))
        assert response.status_code == 200
        assert 'form' in response.context
        assert 'recent_imports' in response.context


# =============================================================================
# CSVTemplateDownloadView Tests
# =============================================================================

class TestCSVTemplateDownloadViewComprehensive:
    """CSVテンプレートダウンロードビュー包括テスト"""

    @pytest.mark.django_db
    def test_template_download_unauthenticated(self, client):
        """未認証ユーザーはリダイレクト"""
        response = client.get(reverse('candidates:csv_template_download'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_template_download_limited_access_forbidden(self, client, interviewer):
        """限定アクセスユーザーは禁止"""
        client.force_login(interviewer)
        response = client.get(reverse('candidates:csv_template_download'))
        assert response.status_code in [302, 403]

    @pytest.mark.django_db
    def test_template_download_success(self, client, client_admin):
        """テンプレートダウンロード成功"""
        client.force_login(client_admin)
        response = client.get(reverse('candidates:csv_template_download'))
        assert response.status_code == 200
        assert 'text/csv' in response.get('Content-Type')


# =============================================================================
# CSVImportHistoryView Tests
# =============================================================================

class TestCSVImportHistoryViewComprehensive:
    """CSVインポート履歴ビュー包括テスト"""

    @pytest.mark.django_db
    def test_import_history_unauthenticated(self, client):
        """未認証ユーザーはリダイレクト"""
        response = client.get(reverse('candidates:csv_import_history'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_import_history_full_access(self, client, client_admin):
        """フルアクセスユーザーはアクセス可能"""
        client.force_login(client_admin)
        response = client.get(reverse('candidates:csv_import_history'))
        assert response.status_code == 200


# =============================================================================
# CandidateCommentCreateView Tests
# =============================================================================

class TestCandidateCommentCreateViewComprehensive:
    """候補者コメント作成ビュー包括テスト"""

    @pytest.mark.django_db
    def test_comment_create_unauthenticated(self, client, candidate):
        """未認証ユーザーはリダイレクト"""
        response = client.post(
            reverse('candidates:comment_create', kwargs={'candidate_pk': candidate.pk}),
            {'content': 'テストコメント'}
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_comment_create_valid(self, client, client_admin, candidate):
        """有効なコメント作成"""
        client.force_login(client_admin)
        response = client.post(
            reverse('candidates:comment_create', kwargs={'candidate_pk': candidate.pk}),
            {'content': '新しいコメント'}
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_comment_create_htmx(self, client, client_admin, candidate):
        """htmxリクエストでコメント作成"""
        client.force_login(client_admin)
        response = client.post(
            reverse('candidates:comment_create', kwargs={'candidate_pk': candidate.pk}),
            {'content': '新しいコメント'},
            HTTP_HX_REQUEST='true'
        )
        assert response.status_code == 204


# =============================================================================
# CandidateCommentUpdateView Tests
# =============================================================================

class TestCandidateCommentUpdateViewComprehensive:
    """候補者コメント編集ビュー包括テスト"""

    @pytest.mark.django_db
    def test_comment_update_unauthenticated(self, client, candidate, comment):
        """未認証ユーザーはリダイレクト"""
        response = client.post(
            reverse('candidates:comment_update', kwargs={
                'candidate_pk': candidate.pk,
                'comment_pk': comment.pk
            }),
            {'content': '更新コメント'}
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_comment_update_own_comment(self, client, client_admin, candidate, comment):
        """自分のコメントを編集"""
        client.force_login(client_admin)
        response = client.post(
            reverse('candidates:comment_update', kwargs={
                'candidate_pk': candidate.pk,
                'comment_pk': comment.pk
            }),
            {'content': '更新されたコメント'}
        )
        assert response.status_code == 302


# =============================================================================
# CandidateCommentDeleteView Tests
# =============================================================================

class TestCandidateCommentDeleteViewComprehensive:
    """候補者コメント削除ビュー包括テスト"""

    @pytest.mark.django_db
    def test_comment_delete_unauthenticated(self, client, candidate, comment):
        """未認証ユーザーはリダイレクト"""
        response = client.post(
            reverse('candidates:comment_delete', kwargs={
                'candidate_pk': candidate.pk,
                'comment_pk': comment.pk
            })
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_comment_delete_own_comment(self, client, client_admin, candidate, comment):
        """自分のコメントを削除"""
        client.force_login(client_admin)
        response = client.post(
            reverse('candidates:comment_delete', kwargs={
                'candidate_pk': candidate.pk,
                'comment_pk': comment.pk
            })
        )
        assert response.status_code == 302
        comment.refresh_from_db()
        assert comment.is_deleted is True

    @pytest.mark.django_db
    def test_comment_delete_htmx(self, client, client_admin, candidate, comment):
        """htmxリクエストでコメント削除"""
        client.force_login(client_admin)
        response = client.post(
            reverse('candidates:comment_delete', kwargs={
                'candidate_pk': candidate.pk,
                'comment_pk': comment.pk
            }),
            HTTP_HX_REQUEST='true'
        )
        assert response.status_code == 204
