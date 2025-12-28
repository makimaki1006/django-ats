"""Django ATS - 候補者モデル

求職者・候補者の情報管理用モデル。

設計ポイント:
- TenantBaseModelを継承（テナント分離）
- 個人情報保護を考慮した設計
- CSVインポート/エクスポート対応
- エージェント経由の登録に対応
- ロールベースのアクセス制御対応
"""

from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator

from apps.core.models import TenantBaseModel


class CandidateQuerySet(models.QuerySet):
    """候補者クエリセット

    ユーザーのロールに応じたフィルタリングを提供。
    """

    def for_user(self, user):
        """ユーザーがアクセス可能な候補者のみを返す

        アクセスルール:
        - フルアクセス（system_admin, consultant, client_admin, hiring_manager, client_recruiter）
          → テナント内の全候補者
        - INTERVIEWER → 担当面接の候補者のみ
        - AGENT → 自社紹介の候補者のみ

        Args:
            user: CustomUserインスタンス

        Returns:
            QuerySet: フィルタリングされた候補者クエリセット
        """
        from apps.accounts.models import UserRole

        # テナントでフィルタ（system_admin以外）
        if user.is_system_admin:
            qs = self.all()
        else:
            qs = self.filter(tenant=user.tenant)

        # フルアクセスの場合はそのまま返す
        if user.has_full_candidate_access:
            return qs

        # 面接官: 担当面接の候補者のみ
        if user.is_interviewer:
            # 自分が面接官（主面接官または同席者）として割り当てられている面接の候補者
            from apps.interviews.models import Interview
            from django.db.models import Q

            # 主面接官として割り当てられている面接
            main_interviewer_ids = Interview.objects.filter(
                tenant=user.tenant,
                interviewer=user
            ).values_list('application__candidate_id', flat=True)

            # 同席者として割り当てられている面接
            additional_interviewer_ids = Interview.objects.filter(
                tenant=user.tenant,
                additional_interviewers=user
            ).values_list('application__candidate_id', flat=True)

            # 両方を結合
            all_candidate_ids = set(main_interviewer_ids) | set(additional_interviewer_ids)
            return qs.filter(id__in=all_candidate_ids)

        # 人材紹介会社: 自社紹介の候補者のみ
        if user.is_agent_user and hasattr(user, 'profile') and user.profile:
            agent_company = user.profile.agent_company
            if agent_company:
                return qs.filter(agent_company=agent_company)
            # エージェント会社が設定されていない場合は空
            return qs.none()

        # その他（想定外のケース）は空を返す
        return qs.none()

    def active(self):
        """アーカイブされていない候補者のみを返す"""
        return self.filter(is_archived=False)

    def archived(self):
        """アーカイブされた候補者のみを返す"""
        return self.filter(is_archived=True)


class CandidateManager(models.Manager):
    """候補者マネージャー

    CandidateQuerySetをデフォルトで使用。
    """

    def get_queryset(self):
        return CandidateQuerySet(self.model, using=self._db)

    def for_user(self, user):
        """ユーザーがアクセス可能な候補者のみを返す"""
        return self.get_queryset().for_user(user)

    def active(self):
        """アーカイブされていない候補者のみを返す"""
        return self.get_queryset().active()

    def archived(self):
        """アーカイブされた候補者のみを返す"""
        return self.get_queryset().archived()


class GenderChoices(models.TextChoices):
    """性別選択肢"""
    MALE = 'male', '男性'
    FEMALE = 'female', '女性'
    OTHER = 'other', 'その他'
    UNSPECIFIED = 'unspecified', '未回答'


class EmploymentStatusChoices(models.TextChoices):
    """現在の就業状況"""
    EMPLOYED = 'employed', '就業中'
    UNEMPLOYED = 'unemployed', '離職中'
    FREELANCE = 'freelance', 'フリーランス'
    STUDENT = 'student', '学生'


class Candidate(TenantBaseModel):
    """候補者モデル

    求職者の基本情報を管理。
    応募（Application）とは1:N関係。

    Attributes:
        name: 氏名
        email: メールアドレス
        phone: 電話番号
        gender: 性別
        birth_date: 生年月日
        current_company: 現職企業
        current_position: 現職役職
        employment_status: 就業状況
        years_of_experience: 経験年数
        desired_salary: 希望年収
        skills: スキル（JSON配列）
        resume_url: 履歴書URL
        agent_company: 紹介元エージェント
        registered_by: 登録者
        notes: 備考
    """

    # 基本情報
    name = models.CharField(
        max_length=100,
        verbose_name='氏名'
    )

    name_kana = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='氏名（カナ）'
    )

    email = models.EmailField(
        verbose_name='メールアドレス'
    )

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="電話番号は正しい形式で入力してください"
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name='電話番号'
    )

    # 個人情報
    gender = models.CharField(
        max_length=15,
        choices=GenderChoices.choices,
        default=GenderChoices.UNSPECIFIED,
        verbose_name='性別'
    )

    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='生年月日'
    )

    address = models.TextField(
        blank=True,
        verbose_name='住所'
    )

    # 職歴情報
    current_company = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='現職企業'
    )

    current_position = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='現職役職'
    )

    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatusChoices.choices,
        default=EmploymentStatusChoices.EMPLOYED,
        verbose_name='就業状況'
    )

    years_of_experience = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(50)],
        verbose_name='経験年数'
    )

    # 希望条件
    desired_salary = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='希望年収（万円）'
    )

    desired_positions = models.JSONField(
        default=list,
        blank=True,
        verbose_name='希望職種',
        help_text='希望職種のリスト'
    )

    desired_locations = models.JSONField(
        default=list,
        blank=True,
        verbose_name='希望勤務地',
        help_text='希望勤務地のリスト'
    )

    can_relocate = models.BooleanField(
        default=False,
        verbose_name='転勤可'
    )

    available_from = models.DateField(
        null=True,
        blank=True,
        verbose_name='入社可能日'
    )

    # スキル・資格
    skills = models.JSONField(
        default=list,
        blank=True,
        verbose_name='スキル',
        help_text='保有スキルのリスト'
    )

    qualifications = models.JSONField(
        default=list,
        blank=True,
        verbose_name='資格',
        help_text='保有資格のリスト'
    )

    education = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='最終学歴'
    )

    # 書類
    resume_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='履歴書URL'
    )

    cv_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='職務経歴書URL'
    )

    # エージェント情報
    agent_company = models.ForeignKey(
        'agents.AgentCompany',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='candidates',
        verbose_name='紹介元エージェント'
    )

    # 登録情報
    registered_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_candidates',
        verbose_name='登録者'
    )

    source = models.ForeignKey(
        'settings_app.ApplicationSource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='candidates',
        verbose_name='流入経路'
    )

    # 備考・メモ
    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )

    # 内部管理用
    is_archived = models.BooleanField(
        default=False,
        verbose_name='アーカイブ済み',
        help_text='アーカイブすると一覧に表示されない'
    )

    # カスタムマネージャー
    objects = CandidateManager()

    class Meta:
        verbose_name = '候補者'
        verbose_name_plural = '候補者'
        ordering = ['-created_at']
        # テナント内でメールアドレスは一意
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'email'],
                name='unique_candidate_email_per_tenant'
            )
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('candidates:candidate_detail', kwargs={'pk': self.pk})

    @property
    def age(self):
        """年齢を計算"""
        if not self.birth_date:
            return None
        from django.utils import timezone
        today = timezone.now().date()
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years

    @property
    def has_resume(self):
        """履歴書があるか"""
        return bool(self.resume_url)

    @property
    def is_from_agent(self):
        """エージェント経由か"""
        return self.agent_company is not None

    @property
    def active_applications_count(self):
        """進行中の応募数"""
        from apps.applications.models import ApplicationStatusChoices
        return self.applications.exclude(
            status__in=[
                ApplicationStatusChoices.REJECTED,
                ApplicationStatusChoices.WITHDRAWN,
                ApplicationStatusChoices.OFFER_DECLINED
            ]
        ).count()


class ImportHistory(TenantBaseModel):
    """CSVインポート履歴モデル

    CSVインポートの実行履歴を記録。
    エラー時のロールバックや再実行のために使用。

    Attributes:
        file_name: インポートファイル名
        status: 処理状態
        total_rows: 総行数
        success_count: 成功件数
        error_count: エラー件数
        error_log: エラー詳細（JSON）
        created_by: 実行者
    """

    class StatusChoices(models.TextChoices):
        PENDING = 'pending', '処理待ち'
        PROCESSING = 'processing', '処理中'
        COMPLETED = 'completed', '完了'
        FAILED = 'failed', '失敗'
        PARTIAL = 'partial', '一部成功'

    file_name = models.CharField(
        max_length=255,
        verbose_name='ファイル名'
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        verbose_name='状態'
    )

    total_rows = models.PositiveIntegerField(
        default=0,
        verbose_name='総行数'
    )

    success_count = models.PositiveIntegerField(
        default=0,
        verbose_name='成功件数'
    )

    error_count = models.PositiveIntegerField(
        default=0,
        verbose_name='エラー件数'
    )

    error_log = models.JSONField(
        default=list,
        blank=True,
        verbose_name='エラーログ',
        help_text='行番号とエラー内容のリスト'
    )

    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='import_histories',
        verbose_name='実行者'
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='処理開始日時'
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='処理完了日時'
    )

    class Meta:
        verbose_name = 'インポート履歴'
        verbose_name_plural = 'インポート履歴'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} ({self.get_status_display()})"

    @property
    def progress_percentage(self):
        """進捗率"""
        if self.total_rows == 0:
            return 0
        processed = self.success_count + self.error_count
        return round(processed / self.total_rows * 100, 1)


class CandidateComment(TenantBaseModel):
    """候補者コメントモデル

    候補者に関するディスカッション・コメントを管理。
    チャット形式でのコミュニケーションを実現。

    設計ポイント:
    - 論理削除（is_deleted）で削除履歴を保持
    - 編集履歴をJSONで保存
    - @メンション機能対応（将来拡張用）

    Attributes:
        candidate: 対象候補者
        author: 投稿者
        content: コメント内容
        is_deleted: 論理削除フラグ
        deleted_at: 削除日時
        deleted_by: 削除者
        edit_history: 編集履歴（JSON）
        mentions: メンションされたユーザー
    """

    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='候補者'
    )

    author = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='candidate_comments',
        verbose_name='投稿者'
    )

    content = models.TextField(
        verbose_name='コメント内容'
    )

    # 論理削除
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='削除済み'
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='削除日時'
    )

    deleted_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_comments',
        verbose_name='削除者'
    )

    # 編集履歴
    edit_history = models.JSONField(
        default=list,
        blank=True,
        verbose_name='編集履歴',
        help_text='編集日時と内容のリスト'
    )

    # メンション（将来拡張用）
    mentions = models.ManyToManyField(
        'accounts.CustomUser',
        blank=True,
        related_name='mentioned_in_comments',
        verbose_name='メンション'
    )

    class Meta:
        verbose_name = 'コメント'
        verbose_name_plural = 'コメント'
        ordering = ['created_at']  # 古い順がデフォルト
        indexes = [
            models.Index(fields=['candidate', 'created_at']),
            models.Index(fields=['author', 'created_at']),
        ]

    def __str__(self):
        truncated = self.content[:30] + '...' if len(self.content) > 30 else self.content
        return f"{self.author.email}: {truncated}"

    @property
    def is_edited(self):
        """編集されたかどうか"""
        return len(self.edit_history) > 0

    @property
    def last_edited_at(self):
        """最終編集日時"""
        if self.edit_history:
            return self.edit_history[-1].get('edited_at')
        return None

    def edit(self, new_content, editor):
        """コメントを編集

        Args:
            new_content: 新しいコメント内容
            editor: 編集者（CustomUser）

        Raises:
            PermissionError: 編集者が投稿者でない場合
        """
        if editor.id != self.author_id:
            raise PermissionError('自分のコメントのみ編集可能です')

        from django.utils import timezone

        # 編集履歴に追加
        self.edit_history.append({
            'edited_at': timezone.now().isoformat(),
            'previous_content': self.content,
        })

        self.content = new_content
        self.save()

    def soft_delete(self, deleter):
        """論理削除

        Args:
            deleter: 削除者（CustomUser）

        Raises:
            PermissionError: 削除者が投稿者でない場合
        """
        if deleter.id != self.author_id:
            raise PermissionError('自分のコメントのみ削除可能です')

        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleter
        self.save()

    def can_edit(self, user):
        """ユーザーが編集可能かどうか"""
        return user.id == self.author_id and not self.is_deleted

    def can_delete(self, user):
        """ユーザーが削除可能かどうか"""
        return user.id == self.author_id and not self.is_deleted
