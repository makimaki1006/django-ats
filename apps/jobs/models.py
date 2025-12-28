"""Django ATS - 求人モデル

求人票・募集ポジションの管理用モデル。

設計ポイント:
- TenantBaseModelを継承（テナント分離）
- ペルソナとN:M関係（JobPersona中間テーブル）
- エージェント会社とN:M関係（JobAgentCompany中間テーブル）
- 複製機能で類似求人を効率的に作成
"""

from django.db import models
from django.core.validators import MinValueValidator

from apps.core.models import TenantBaseModel


class JobStatusChoices(models.TextChoices):
    """求人ステータス"""
    DRAFT = 'draft', '下書き'
    ACTIVE = 'active', '募集中'
    PAUSED = 'paused', '一時停止'
    CLOSED = 'closed', '募集終了'


class EmploymentTypeChoices(models.TextChoices):
    """雇用形態"""
    FULL_TIME = 'full_time', '正社員'
    CONTRACT = 'contract', '契約社員'
    PART_TIME = 'part_time', 'パート・アルバイト'
    TEMPORARY = 'temporary', '派遣社員'
    INTERN = 'intern', 'インターン'


class Job(TenantBaseModel):
    """求人モデル

    募集中のポジション情報を管理。

    Attributes:
        title: 求人タイトル
        unique_code: 求人コード（社内管理用）
        status: 募集ステータス
        department: 部門
        employment_type: 雇用形態
        location: 勤務地
        salary_min: 年収下限
        salary_max: 年収上限
        description: 仕事内容
        requirements: 応募要件
        benefits: 待遇・福利厚生
        personas: 紐付くペルソナ
        agent_companies: 依頼エージェント
        created_by: 作成者
    """

    title = models.CharField(
        max_length=255,
        verbose_name='求人タイトル'
    )

    unique_code = models.CharField(
        max_length=50,
        verbose_name='求人コード',
        help_text='社内管理用の識別コード'
    )

    status = models.CharField(
        max_length=20,
        choices=JobStatusChoices.choices,
        default=JobStatusChoices.DRAFT,
        verbose_name='ステータス'
    )

    # 組織情報
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='部門'
    )

    team = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='チーム'
    )

    hiring_manager = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_jobs',
        verbose_name='採用責任者'
    )

    # 雇用条件
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentTypeChoices.choices,
        default=EmploymentTypeChoices.FULL_TIME,
        verbose_name='雇用形態'
    )

    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='勤務地'
    )

    remote_policy = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='リモートワーク',
        help_text='例: フルリモート可、週2日出社、出社必須など'
    )

    # 年収
    salary_min = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='年収下限（万円）'
    )

    salary_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='年収上限（万円）'
    )

    salary_notes = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='年収補足',
        help_text='例: 経験・スキルに応じて決定'
    )

    # 求人内容
    description = models.TextField(
        blank=True,
        verbose_name='仕事内容'
    )

    requirements = models.TextField(
        blank=True,
        verbose_name='応募要件'
    )

    preferred_requirements = models.TextField(
        blank=True,
        verbose_name='歓迎要件'
    )

    benefits = models.TextField(
        blank=True,
        verbose_name='待遇・福利厚生'
    )

    # 選考プロセス
    selection_process = models.TextField(
        blank=True,
        verbose_name='選考プロセス',
        help_text='例: 書類選考 → 一次面接 → 二次面接 → 最終面接'
    )

    # 募集情報
    headcount = models.PositiveIntegerField(
        default=1,
        verbose_name='募集人数'
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='公開日時'
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='募集終了日時'
    )

    deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name='応募締切日'
    )

    # ペルソナ（N:M）
    personas = models.ManyToManyField(
        'personas.Persona',
        through='JobPersona',
        related_name='jobs',
        blank=True,
        verbose_name='ペルソナ'
    )

    # エージェント会社（N:M）
    agent_companies = models.ManyToManyField(
        'agents.AgentCompany',
        through='JobAgentCompany',
        related_name='assigned_jobs',
        blank=True,
        verbose_name='依頼エージェント'
    )

    # メタ情報
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_jobs',
        verbose_name='作成者'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='社内メモ'
    )

    class Meta:
        verbose_name = '求人'
        verbose_name_plural = '求人'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'unique_code'],
                name='unique_job_code_per_tenant'
            )
        ]

    def __str__(self):
        return f"{self.unique_code}: {self.title}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('jobs:job_detail', kwargs={'pk': self.pk})

    @property
    def salary_range_display(self):
        """年収範囲の表示"""
        if self.salary_min and self.salary_max:
            return f"{self.salary_min}万円〜{self.salary_max}万円"
        elif self.salary_min:
            return f"{self.salary_min}万円以上"
        elif self.salary_max:
            return f"〜{self.salary_max}万円"
        return "応相談"

    @property
    def is_active(self):
        """募集中かどうか"""
        return self.status == JobStatusChoices.ACTIVE

    @property
    def application_count(self):
        """応募数"""
        return self.applications.count()

    def publish(self):
        """求人を公開"""
        from django.utils import timezone
        self.status = JobStatusChoices.ACTIVE
        self.published_at = timezone.now()
        self.save(update_fields=['status', 'published_at', 'updated_at'])

    def pause(self):
        """求人を一時停止"""
        self.status = JobStatusChoices.PAUSED
        self.save(update_fields=['status', 'updated_at'])

    def close(self):
        """求人を終了"""
        from django.utils import timezone
        self.status = JobStatusChoices.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at', 'updated_at'])

    def duplicate(self, new_code=None, new_title=None):
        """求人を複製"""
        old_personas = list(self.personas.all())
        old_agents = list(self.agent_companies.all())

        job_copy = Job.objects.get(pk=self.pk)
        job_copy.pk = None
        job_copy.unique_code = new_code or f"{self.unique_code}_copy"
        job_copy.title = new_title or f"{self.title} (コピー)"
        job_copy.status = JobStatusChoices.DRAFT
        job_copy.published_at = None
        job_copy.closed_at = None
        job_copy.save()

        # ペルソナを複製
        for persona in old_personas:
            JobPersona.objects.create(job=job_copy, persona=persona)

        # エージェント会社を複製
        for agent in old_agents:
            JobAgentCompany.objects.create(job=job_copy, agent_company=agent)

        return job_copy


class JobPersona(models.Model):
    """求人-ペルソナ中間テーブル

    求人とペルソナの紐付けを管理。
    優先度や備考を追加可能。
    """

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='job_personas',
        verbose_name='求人'
    )

    persona = models.ForeignKey(
        'personas.Persona',
        on_delete=models.CASCADE,
        related_name='persona_jobs',
        verbose_name='ペルソナ'
    )

    priority = models.PositiveIntegerField(
        default=1,
        verbose_name='優先度',
        help_text='1が最優先'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )

    class Meta:
        verbose_name = '求人ペルソナ'
        verbose_name_plural = '求人ペルソナ'
        ordering = ['priority']
        unique_together = ['job', 'persona']

    def __str__(self):
        return f"{self.job.title} - {self.persona.name}"


class JobAgentCompany(models.Model):
    """求人-エージェント会社中間テーブル

    求人とエージェント会社の紐付けを管理。
    依頼日、特別手数料率などを記録。
    """

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='job_agent_companies',
        verbose_name='求人'
    )

    agent_company = models.ForeignKey(
        'agents.AgentCompany',
        on_delete=models.CASCADE,
        related_name='agent_jobs',
        verbose_name='エージェント会社'
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='依頼日時'
    )

    special_fee_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='特別手数料率（%）',
        help_text='設定しない場合はエージェント会社のデフォルト手数料率を適用'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )

    class Meta:
        verbose_name = '求人エージェント'
        verbose_name_plural = '求人エージェント'
        ordering = ['-assigned_at']
        unique_together = ['job', 'agent_company']

    def __str__(self):
        return f"{self.job.title} - {self.agent_company.name}"

    @property
    def fee_rate(self):
        """適用される手数料率"""
        return self.special_fee_rate or self.agent_company.fee_rate
