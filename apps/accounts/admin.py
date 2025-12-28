"""
Django ATS - Accounts Admin
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Profile
from .forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """カスタムユーザー管理"""

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = [
        'email',
        'full_name',
        'role',
        'tenant',
        'is_active',
        'is_staff',
        'last_login',
    ]
    list_filter = ['role', 'is_active', 'is_staff', 'tenant']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('個人情報', {'fields': ('first_name', 'last_name')}),
        ('権限', {'fields': ('role', 'tenant', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('日時', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role', 'tenant', 'is_active', 'is_staff'),
        }),
    )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = '氏名'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """プロファイル管理"""

    list_display = ['user', 'phone', 'department', 'position', 'tenant']
    list_filter = ['tenant', 'department']
    search_fields = ['user__email', 'phone', 'department', 'position']
    raw_id_fields = ['user', 'tenant']
