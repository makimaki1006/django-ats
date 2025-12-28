"""Django ATS - Google Sheets連携サービス

テナントごとのGoogle Spreadsheet操作を管理。
"""

from .client import SheetsClient
from .exceptions import (
    SheetsError,
    SheetsAuthError,
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsRateLimitError,
    SheetsValidationError,
)
from .repositories import (
    CandidateRepository,
    JobRepository,
    ApplicationRepository,
    InterviewRepository,
    SheetsRepositoryFactory,
)
from .onboarding import (
    TenantOnboardingService,
    get_tenant_repository_factory,
)

__all__ = [
    # クライアント
    'SheetsClient',
    # 例外
    'SheetsError',
    'SheetsAuthError',
    'SheetsNotFoundError',
    'SheetsPermissionError',
    'SheetsRateLimitError',
    'SheetsValidationError',
    # リポジトリ
    'CandidateRepository',
    'JobRepository',
    'ApplicationRepository',
    'InterviewRepository',
    'SheetsRepositoryFactory',
    # オンボーディング
    'TenantOnboardingService',
    'get_tenant_repository_factory',
]
