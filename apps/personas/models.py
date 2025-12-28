"""Django ATS - ペルソナモデル

理想的な候補者像（ペルソナ）の管理用モデル。

設計ポイント:
- TenantBaseModelを継承（テナント分離）
- 求人とN:M関係（JobPersona中間テーブル）
- テンプレート機能（is_template）で再利用可能
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.core.models import TenantBaseModel


class Persona(TenantBaseModel):
    """ペルソナモデル

    理想的な候補者像を定義。
    複数の求人で共通して使用可能。

    Attributes:
        name: ペルソナ名
        description: 詳細説明
        is_template: テンプレートフラグ
        age_min: 最小年齢
        age_max: 最大年齢
        experience_years_min: 最小経験年数
        required_skills: 必須スキル
        preferred_skills: 歓迎スキル
        education_level: 学歴要件
        personality_traits: 人物像・性格
        work_style: 働き方
        motivation: 志向性
    """

    name = models.CharField(
        max_length=100,
        verbose_name='ペルソナ名'
    )

    description = models.TextField(
        blank=True,
        verbose_name='詳細説明'
    )

    is_template = models.BooleanField(
        default=False,
        verbose_name='テンプレート',
        help_text='テンプレートとして保存すると他の求人で再利用可能'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )

    # 年齢要件
    age_min = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(18), MaxValueValidator(100)],
        verbose_name='最小年齢'
    )

    age_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(18), MaxValueValidator(100)],
        verbose_name='最大年齢'
    )

    # 経験要件
    experience_years_min = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(50)],
        verbose_name='最小経験年数'
    )

    experience_years_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(50)],
        verbose_name='最大経験年数'
    )

    # スキル要件
    required_skills = models.JSONField(
        default=list,
        blank=True,
        verbose_name='必須スキル',
        help_text='必須スキルのリスト'
    )

    preferred_skills = models.JSONField(
        default=list,
        blank=True,
        verbose_name='歓迎スキル',
        help_text='歓迎スキルのリスト'
    )

    # 学歴要件
    class EducationLevelChoices(models.TextChoices):
        NONE = 'none', '不問'
        HIGH_SCHOOL = 'high_school', '高卒以上'
        VOCATIONAL = 'vocational', '専門卒以上'
        ASSOCIATE = 'associate', '短大卒以上'
        BACHELOR = 'bachelor', '大卒以上'
        MASTER = 'master', '修士以上'
        DOCTOR = 'doctor', '博士以上'

    education_level = models.CharField(
        max_length=20,
        choices=EducationLevelChoices.choices,
        default=EducationLevelChoices.NONE,
        verbose_name='学歴要件'
    )

    # 人物像
    personality_traits = models.JSONField(
        default=list,
        blank=True,
        verbose_name='人物像・性格',
        help_text='求める性格特性のリスト'
    )

    work_style = models.TextField(
        blank=True,
        verbose_name='働き方',
        help_text='求める働き方の説明'
    )

    motivation = models.TextField(
        blank=True,
        verbose_name='志向性',
        help_text='求める志向性・モチベーション'
    )

    # 補足
    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )

    # 作成者
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_personas',
        verbose_name='作成者'
    )

    class Meta:
        verbose_name = 'ペルソナ'
        verbose_name_plural = 'ペルソナ'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('personas:detail', kwargs={'pk': self.pk})

    @property
    def age_range_display(self):
        """年齢範囲の表示"""
        if self.age_min and self.age_max:
            return f"{self.age_min}〜{self.age_max}歳"
        elif self.age_min:
            return f"{self.age_min}歳以上"
        elif self.age_max:
            return f"{self.age_max}歳以下"
        return "不問"

    @property
    def experience_range_display(self):
        """経験年数範囲の表示"""
        if self.experience_years_min and self.experience_years_max:
            return f"{self.experience_years_min}〜{self.experience_years_max}年"
        elif self.experience_years_min:
            return f"{self.experience_years_min}年以上"
        elif self.experience_years_max:
            return f"{self.experience_years_max}年以下"
        return "不問"

    def duplicate(self, new_name=None):
        """ペルソナを複製"""
        persona_copy = Persona.objects.get(pk=self.pk)
        persona_copy.pk = None
        persona_copy.name = new_name or f"{self.name} (コピー)"
        persona_copy.is_template = False
        persona_copy.save()
        return persona_copy
