"""Django ATS - アカウントモデル

ユーザー認証・プロファイル管理用モデル。

設計ポイント:
- AbstractUserを継承したCustomUserでメール認証
- ロールベースアクセス制御（RBAC）
- Profile はユーザーの追加情報（テナント所属）
- エージェントはagent_companyに紐付く
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator

from apps.core.models import TenantBaseModel


class UserRoleChoices(models.TextChoices):
    """ユーザーロール定義

    権限マトリクス:
    - system_admin: 全テナント横断アクセス、システム設定管理
    - consultant: テナント内全候補者アクセス、設定支援、レポート確認
    - client_admin: テナント設定、ユーザー招待、全機能アクセス（人事担当者）
    - hiring_manager: テナント内全候補者アクセス、承認、レポート確認（採用責任者）
    - client_recruiter: 応募者・求人・面接管理
    - interviewer: 担当面接の候補者のみ閲覧・評価入力
    - agent: 自社登録応募者のみ閲覧・登録（人材紹介会社）

    アクセスレベル:
    - フルアクセス: system_admin, consultant, client_admin, hiring_manager, client_recruiter
    - 限定アクセス: interviewer（担当面接のみ）, agent（自社紹介のみ）
    """
    SYSTEM_ADMIN = 'system_admin', 'システム管理者'
    CONSULTANT = 'consultant', '採用コンサルタント'
    CLIENT_ADMIN = 'client_admin', '人事担当者'
    HIRING_MANAGER = 'hiring_manager', '採用責任者'
    CLIENT_RECRUITER = 'client_recruiter', '企業担当者'
    INTERVIEWER = 'interviewer', '面接官'
    AGENT = 'agent', '人材紹介会社'


# 後方互換性のためのエイリアス
UserRole = UserRoleChoices


class CustomUserManager(BaseUserManager):
    """カスタムユーザーマネージャー

    メールアドレスをユーザー名として使用。
    """

    def create_user(self, email, password=None, **extra_fields):
        """通常ユーザーを作成"""
        if not email:
            raise ValueError('メールアドレスは必須です')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """スーパーユーザーを作成"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.SYSTEM_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('スーパーユーザーはis_staff=Trueである必要があります')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('スーパーユーザーはis_superuser=Trueである必要があります')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """カスタムユーザーモデル

    Djangoの標準Userモデルを拡張。
    メールアドレスで認証、ロールベースの権限管理。

    Attributes:
        id: UUID主キー
        email: メールアドレス（ログインID）
        tenant: 所属テナント
        role: ユーザーロール
        is_email_verified: メール認証済みフラグ
    """
    # AbstractUserのusernameを無効化
    username = None

    # UUID主キー
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # メールアドレス（ログインID）
    email = models.EmailField(
        unique=True,
        verbose_name='メールアドレス'
    )

    # テナント（system_adminはnull可）
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='テナント'
    )

    # ロール
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CLIENT_RECRUITER,
        verbose_name='ロール'
    )

    # メール認証
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name='メール認証済み'
    )

    # タイムスタンプ（AbstractUserにはlast_loginがある）
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    def get_full_name(self):
        """フルネーム取得（Profileから）"""
        if hasattr(self, 'profile') and self.profile:
            return self.profile.display_name or self.email
        return self.email

    def get_short_name(self):
        """短い名前（メールのローカルパート）"""
        return self.email.split('@')[0]

    @property
    def display_name(self):
        """表示名"""
        return self.get_full_name()

    @property
    def full_name(self):
        """氏名（姓 + 名）"""
        parts = [self.last_name, self.first_name]
        return ' '.join(p for p in parts if p)

    @property
    def is_system_admin(self):
        """システム管理者かどうか"""
        return self.role == UserRole.SYSTEM_ADMIN

    @property
    def is_consultant(self):
        """採用コンサルタントかどうか"""
        return self.role == UserRole.CONSULTANT

    @property
    def is_admin(self):
        """管理者権限を持つかどうか（テナント設定変更可能）"""
        return self.role in [
            UserRole.SYSTEM_ADMIN,
            UserRole.CONSULTANT,
            UserRole.CLIENT_ADMIN
        ]

    @property
    def is_hiring_manager(self):
        """採用責任者かどうか"""
        return self.role == UserRole.HIRING_MANAGER

    @property
    def is_recruiter(self):
        """採用担当者以上かどうか（日常操作が可能）"""
        return self.role in [
            UserRole.SYSTEM_ADMIN,
            UserRole.CONSULTANT,
            UserRole.CLIENT_ADMIN,
            UserRole.HIRING_MANAGER,
            UserRole.CLIENT_RECRUITER
        ]

    @property
    def is_interviewer(self):
        """面接官かどうか"""
        return self.role == UserRole.INTERVIEWER

    @property
    def is_agent_user(self):
        """人材紹介会社ユーザーかどうか"""
        return self.role == UserRole.AGENT

    @property
    def has_full_candidate_access(self):
        """全候補者へのフルアクセス権を持つかどうか

        Returns:
            bool: フルアクセス権がある場合True
        """
        return self.role in [
            UserRole.SYSTEM_ADMIN,
            UserRole.CONSULTANT,
            UserRole.CLIENT_ADMIN,
            UserRole.HIRING_MANAGER,
            UserRole.CLIENT_RECRUITER
        ]

    @property
    def has_limited_candidate_access(self):
        """候補者への限定アクセス権を持つかどうか

        - INTERVIEWER: 担当面接の候補者のみ
        - AGENT: 自社紹介の候補者のみ

        Returns:
            bool: 限定アクセスの場合True
        """
        return self.role in [
            UserRole.INTERVIEWER,
            UserRole.AGENT
        ]

    def can_access_tenant(self, tenant):
        """指定テナントにアクセス可能かどうか"""
        if self.is_system_admin:
            return True
        return self.tenant_id == tenant.id if tenant else False


class Profile(TenantBaseModel):
    """ユーザープロファイルモデル

    ユーザーの追加情報を管理。
    CustomUserとは1:1で紐付く。

    Attributes:
        user: 紐付くユーザー
        display_name: 表示名
        phone: 電話番号
        avatar_url: アバター画像URL
        agent_company: エージェント会社（エージェントユーザーのみ）
        notification_settings: 通知設定（JSON）
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='ユーザー'
    )

    display_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='表示名'
    )

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="電話番号は '+999999999' の形式で入力してください。最大15桁。"
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name='電話番号'
    )

    avatar_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='アバターURL'
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='アバター画像'
    )

    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='部署'
    )

    position = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='役職'
    )

    # エージェント会社（エージェントユーザーのみ）
    agent_company = models.ForeignKey(
        'agents.AgentCompany',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles',
        verbose_name='エージェント会社'
    )

    # 通知設定
    notification_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='通知設定',
        help_text='通知のオン/オフ設定をJSON形式で保存'
    )

    class Meta:
        verbose_name = 'プロファイル'
        verbose_name_plural = 'プロファイル'

    def __str__(self):
        return f"{self.display_name or self.user.email} のプロファイル"

    def get_notification_setting(self, key, default=True):
        """通知設定を取得"""
        return self.notification_settings.get(key, default)

    def set_notification_setting(self, key, value):
        """通知設定を保存"""
        self.notification_settings[key] = value
        self.save(update_fields=['notification_settings', 'updated_at'])
