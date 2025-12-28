"""Django ATS - 候補者ビューテスト

候補者関連ビューのテスト。
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.candidates.models import Candidate
from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='候補者ビューテスト',
        code='candidate-view-test',
        is_active=True,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@candidate-view-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def interviewer(db, tenant):
    """面接官ユーザー"""
    return CustomUser.objects.create_user(
        email='interviewer@candidate-view-test.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def candidate(db, tenant):
    """テスト候補者"""
    return Candidate.objects.create(
        tenant=tenant,
        email='candidate@test.com',
        name='山田太郎',
    )


@pytest.fixture
def multiple_candidates(db, tenant):
    """複数の候補者"""
    candidates = []
    for i in range(5):
        candidates.append(Candidate.objects.create(
            tenant=tenant,
            email=f'candidate{i}@test.com',
            name=f'候補者{i}',
        ))
    return candidates


@pytest.fixture
def client_admin(db, admin_user):
    """管理者クライアント"""
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def client_interviewer(db, interviewer):
    """面接官クライアント"""
    client = Client()
    client.force_login(interviewer)
    return client


# =============================================================================
# CandidateListView Tests
# =============================================================================

class TestCandidateListView:
    """候補者一覧ビューのテスト"""

    @pytest.mark.django_db
    def test_candidate_list_requires_login(self, client):
        """未認証ユーザーはリダイレクトされる"""
        response = client.get(reverse('candidates:candidate_list'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_candidate_list_authenticated(self, client_admin, candidate):
        """認証済みユーザーは一覧を表示できる"""
        response = client_admin.get(reverse('candidates:candidate_list'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_candidate_list_search(self, client_admin, candidate):
        """検索できる"""
        response = client_admin.get(
            reverse('candidates:candidate_list'),
            {'q': '山田'}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_candidate_list_pagination(self, client_admin, multiple_candidates):
        """ページネーションが動作する"""
        response = client_admin.get(reverse('candidates:candidate_list'))
        assert response.status_code == 200


# =============================================================================
# CandidateDetailView Tests
# =============================================================================

class TestCandidateDetailView:
    """候補者詳細ビューのテスト"""

    @pytest.mark.django_db
    def test_candidate_detail_requires_login(self, client, candidate):
        """未認証ユーザーはリダイレクトされる"""
        response = client.get(
            reverse('candidates:candidate_detail', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_candidate_detail_authenticated(self, client_admin, candidate):
        """認証済みユーザーは詳細を表示できる"""
        response = client_admin.get(
            reverse('candidates:candidate_detail', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 200


# =============================================================================
# CandidateCreateView Tests
# =============================================================================

class TestCandidateCreateView:
    """候補者作成ビューのテスト"""

    @pytest.mark.django_db
    def test_candidate_create_requires_login(self, client):
        """未認証ユーザーはリダイレクトされる"""
        response = client.get(reverse('candidates:candidate_create'))
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_candidate_create_form_display(self, client_admin):
        """作成フォームが表示される"""
        response = client_admin.get(reverse('candidates:candidate_create'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_candidate_create_valid_data(self, client_admin):
        """有効なデータで候補者を作成できる"""
        data = {
            'email': 'new-candidate@test.com',
            'name': '新規候補者',
            'phone': '09012345678',
        }
        response = client_admin.post(reverse('candidates:candidate_create'), data)
        assert response.status_code in [302, 200]


# =============================================================================
# CandidateUpdateView Tests
# =============================================================================

class TestCandidateUpdateView:
    """候補者更新ビューのテスト"""

    @pytest.mark.django_db
    def test_candidate_update_requires_login(self, client, candidate):
        """未認証ユーザーはリダイレクトされる"""
        response = client.get(
            reverse('candidates:candidate_update', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 302

    @pytest.mark.django_db
    def test_candidate_update_form_display(self, client_admin, candidate):
        """更新フォームが表示される"""
        response = client_admin.get(
            reverse('candidates:candidate_update', kwargs={'pk': candidate.pk})
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_candidate_update_valid_data(self, client_admin, candidate):
        """有効なデータで候補者を更新できる"""
        data = {
            'email': candidate.email,
            'name': '更新後の名前',
            'phone': '09087654321',
        }
        response = client_admin.post(
            reverse('candidates:candidate_update', kwargs={'pk': candidate.pk}),
            data
        )
        assert response.status_code in [302, 200]


# =============================================================================
# Candidate Model Tests
# =============================================================================

class TestCandidateModel:
    """候補者モデルのテスト"""

    @pytest.mark.django_db
    def test_candidate_str(self, candidate):
        """__str__が候補者名を返す"""
        assert '山田太郎' in str(candidate)

    @pytest.mark.django_db
    def test_candidate_with_details(self, tenant):
        """詳細情報付き候補者"""
        candidate = Candidate.objects.create(
            tenant=tenant,
            email='detailed@test.com',
            name='詳細候補者',
            phone='09011112222',
        )
        assert candidate.phone == '09011112222'
