"""Django ATS - エージェントモデル

人材紹介会社（エージェント）の管理用モデル。

設計ポイント:
- AgentCompanyはマスターデータ（全テナント共通可能）
- is_globalフラグで全テナント共通/テナント固有を区別
- 契約情報、手数料率などの管理
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.core.models import BaseModel


class AgentCompany(BaseModel):
    """エージェント会社モデル

    人材紹介会社の情報を管理。
    テナント固有 or 全テナント共通として登録可能。

    Attributes:
        name: 会社名
        code: 会社コード（一意）
        tenant: 所属テナント（nullなら全テナント共通）
        contact_email: 連絡先メール
        contact_phone: 連絡先電話番号
        fee_rate: 紹介手数料率（%）
        contract_start_date: 契約開始日
        contract_end_date: 契約終了日
        is_active: 有効フラグ
        notes: 備考
    """

    name = models.CharField(
        max_length=255,
        verbose_name='会社名'
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='会社コード',
        help_text='社内管理用の一意識別子'
    )

    # テナント（nullなら全テナント共通マスター）
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='agent_companies',
        verbose_name='テナント',
        help_text='空欄の場合は全テナント共通'
    )

    # 連絡先情報
    contact_email = models.EmailField(
        blank=True,
        verbose_name='連絡先メール'
    )

    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='連絡先電話番号'
    )

    contact_person = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='担当者名'
    )

    # 契約情報
    fee_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        verbose_name='紹介手数料率（%）',
        help_text='成功報酬の割合（年収の何%）'
    )

    contract_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='契約開始日'
    )

    contract_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='契約終了日'
    )

    # 状態
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効',
        help_text='無効にすると新規紹介を受け付けない'
    )

    is_preferred = models.BooleanField(
        default=False,
        verbose_name='優先パートナー',
        help_text='優先的に案件を紹介するパートナー'
    )

    # 住所情報
    address = models.TextField(
        blank=True,
        verbose_name='住所'
    )

    website = models.URLField(
        blank=True,
        null=True,
        verbose_name='Webサイト'
    )

    # 備考
    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )

    # 統計用キャッシュ（オプション）
    total_candidates = models.PositiveIntegerField(
        default=0,
        verbose_name='紹介候補者数'
    )

    total_placements = models.PositiveIntegerField(
        default=0,
        verbose_name='採用決定数'
    )

    class Meta:
        verbose_name = 'エージェント会社'
        verbose_name_plural = 'エージェント会社'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('agents:detail', kwargs={'pk': self.pk})

    @property
    def is_global(self):
        """全テナント共通マスターかどうか"""
        return self.tenant is None

    @property
    def is_contract_active(self):
        """契約が有効期間内かどうか"""
        from django.utils import timezone
        today = timezone.now().date()

        if self.contract_start_date and today < self.contract_start_date:
            return False
        if self.contract_end_date and today > self.contract_end_date:
            return False
        return True

    @property
    def placement_rate(self):
        """採用率（候補者→採用の割合）"""
        if self.total_candidates == 0:
            return 0
        return round(self.total_placements / self.total_candidates * 100, 1)

    def update_statistics(self):
        """統計情報を更新（バッチ処理で使用）"""
        self.total_candidates = self.candidates.count()
        self.total_placements = self.candidates.filter(
            applications__status='内定承諾'
        ).distinct().count()
        self.save(update_fields=['total_candidates', 'total_placements', 'updated_at'])
