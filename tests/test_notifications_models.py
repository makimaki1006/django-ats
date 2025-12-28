"""Django ATS - 通知モデルテスト

Notification モデルのテスト。
"""

import pytest
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationTypeChoices,
    NotificationPriorityChoices,
)
from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='通知テスト',
        code='notification-test',
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """テストユーザー"""
    return CustomUser.objects.create_user(
        email='user@notification-test.com',
        password='testpass123',
        role=UserRoleChoices.INTERVIEWER,
        tenant=tenant,
    )


@pytest.fixture
def other_user(db, tenant):
    """別ユーザー"""
    return CustomUser.objects.create_user(
        email='other@notification-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def notification(db, tenant, user):
    """テスト通知"""
    return Notification.objects.create(
        tenant=tenant,
        user=user,
        notification_type=NotificationTypeChoices.NEW_APPLICATION,
        title='新規応募がありました',
        message='山田太郎さんから応募がありました。',
    )


# =============================================================================
# Basic Model Tests
# =============================================================================

class TestNotificationModel:
    """Notification モデルのテスト"""

    @pytest.mark.django_db
    def test_create_notification(self, tenant, user):
        """通知を作成できる"""
        notification = Notification.objects.create(
            tenant=tenant,
            user=user,
            title='テスト通知',
        )
        assert notification.pk is not None
        assert notification.title == 'テスト通知'
        assert notification.is_read is False

    @pytest.mark.django_db
    def test_str_method(self, notification, user):
        """__str__がユーザーとタイトルを返す"""
        assert user.email in str(notification)
        assert notification.title in str(notification)

    @pytest.mark.django_db
    def test_default_values(self, tenant, user):
        """デフォルト値が正しく設定される"""
        notification = Notification.objects.create(
            tenant=tenant,
            user=user,
            title='デフォルトテスト',
        )
        assert notification.notification_type == NotificationTypeChoices.SYSTEM
        assert notification.priority == NotificationPriorityChoices.NORMAL
        assert notification.is_read is False
        assert notification.read_at is None


# =============================================================================
# Icon Property Tests
# =============================================================================

class TestNotificationIcon:
    """通知アイコンのテスト"""

    @pytest.mark.django_db
    def test_new_application_icon(self, tenant, user):
        """新規応募アイコン"""
        notification = Notification.objects.create(
            tenant=tenant,
            user=user,
            notification_type=NotificationTypeChoices.NEW_APPLICATION,
            title='テスト',
        )
        assert notification.icon == 'user-plus'

    @pytest.mark.django_db
    def test_status_change_icon(self, tenant, user):
        """ステータス変更アイコン"""
        notification = Notification.objects.create(
            tenant=tenant,
            user=user,
            notification_type=NotificationTypeChoices.STATUS_CHANGE,
            title='テスト',
        )
        assert notification.icon == 'refresh-cw'

    @pytest.mark.django_db
    def test_interview_reminder_icon(self, tenant, user):
        """面接リマインドアイコン"""
        notification = Notification.objects.create(
            tenant=tenant,
            user=user,
            notification_type=NotificationTypeChoices.INTERVIEW_REMINDER,
            title='テスト',
        )
        assert notification.icon == 'bell'

    @pytest.mark.django_db
    def test_all_icons(self, tenant, user):
        """全通知タイプのアイコン"""
        expected_icons = {
            NotificationTypeChoices.NEW_APPLICATION: 'user-plus',
            NotificationTypeChoices.STATUS_CHANGE: 'refresh-cw',
            NotificationTypeChoices.INTERVIEW_REMINDER: 'bell',
            NotificationTypeChoices.INTERVIEW_SCHEDULED: 'calendar',
            NotificationTypeChoices.INTERVIEW_COMPLETED: 'check-circle',
            NotificationTypeChoices.FEEDBACK_REQUEST: 'message-square',
            NotificationTypeChoices.PENDING_DEADLINE: 'clock',
            NotificationTypeChoices.OFFER_MADE: 'gift',
            NotificationTypeChoices.OFFER_RESPONSE: 'mail',
            NotificationTypeChoices.SYSTEM: 'info',
        }
        for notification_type, expected_icon in expected_icons.items():
            notification = Notification.objects.create(
                tenant=tenant,
                user=user,
                notification_type=notification_type,
                title='テスト',
            )
            assert notification.icon == expected_icon, f"{notification_type} icon mismatch"


# =============================================================================
# Mark As Read Tests
# =============================================================================

class TestMarkAsRead:
    """既読処理のテスト"""

    @pytest.mark.django_db
    def test_mark_as_read(self, notification):
        """既読にできる"""
        assert notification.is_read is False
        assert notification.read_at is None

        notification.mark_as_read()

        assert notification.is_read is True
        assert notification.read_at is not None

    @pytest.mark.django_db
    def test_mark_as_read_already_read(self, notification):
        """既に既読の場合は更新されない"""
        notification.mark_as_read()
        original_read_at = notification.read_at

        # 再度既読にしても変わらない
        notification.mark_as_read()

        notification.refresh_from_db()
        assert notification.read_at == original_read_at


# =============================================================================
# Create Notification Class Method Tests
# =============================================================================

class TestCreateNotification:
    """create_notificationメソッドのテスト"""

    @pytest.mark.django_db
    def test_create_notification_basic(self, tenant, user):
        """基本的な通知作成"""
        notification = Notification.create_notification(
            tenant=tenant,
            user=user,
            notification_type=NotificationTypeChoices.NEW_APPLICATION,
            title='新規応募',
        )
        assert notification.pk is not None
        assert notification.title == '新規応募'
        assert notification.tenant == tenant
        assert notification.user == user

    @pytest.mark.django_db
    def test_create_notification_with_all_options(self, tenant, user):
        """全オプション付き通知作成"""
        notification = Notification.create_notification(
            tenant=tenant,
            user=user,
            notification_type=NotificationTypeChoices.INTERVIEW_SCHEDULED,
            title='面接スケジュール',
            message='面接が設定されました',
            link='/interviews/1/',
            priority=NotificationPriorityChoices.HIGH,
            metadata={'interview_id': 1},
        )
        assert notification.message == '面接が設定されました'
        assert notification.link == '/interviews/1/'
        assert notification.priority == NotificationPriorityChoices.HIGH
        assert notification.metadata == {'interview_id': 1}

    @pytest.mark.django_db
    def test_create_notification_with_related_object(self, tenant, user):
        """関連オブジェクト付き通知作成"""
        # テナント自体を関連オブジェクトとして使用
        notification = Notification.create_notification(
            tenant=tenant,
            user=user,
            notification_type=NotificationTypeChoices.SYSTEM,
            title='関連オブジェクトテスト',
            related_object=tenant,
        )
        assert notification.related_object_type == 'Tenant'
        assert notification.related_object_id == str(tenant.pk)


# =============================================================================
# Get Unread Count Tests
# =============================================================================

class TestGetUnreadCount:
    """未読カウントのテスト"""

    @pytest.mark.django_db
    def test_get_unread_count_zero(self, tenant, user):
        """未読通知がない場合"""
        count = Notification.get_unread_count(user)
        assert count == 0

    @pytest.mark.django_db
    def test_get_unread_count_multiple(self, tenant, user):
        """複数の未読通知"""
        for i in range(5):
            Notification.objects.create(
                tenant=tenant,
                user=user,
                title=f'通知{i}',
            )

        count = Notification.get_unread_count(user)
        assert count == 5

    @pytest.mark.django_db
    def test_get_unread_count_mixed(self, tenant, user):
        """既読・未読混在"""
        for i in range(3):
            Notification.objects.create(
                tenant=tenant,
                user=user,
                title=f'未読{i}',
                is_read=False,
            )
        for i in range(2):
            Notification.objects.create(
                tenant=tenant,
                user=user,
                title=f'既読{i}',
                is_read=True,
            )

        count = Notification.get_unread_count(user)
        assert count == 3


# =============================================================================
# Mark All As Read Tests
# =============================================================================

class TestMarkAllAsRead:
    """全既読処理のテスト"""

    @pytest.mark.django_db
    def test_mark_all_as_read(self, tenant, user):
        """全て既読にできる"""
        for i in range(5):
            Notification.objects.create(
                tenant=tenant,
                user=user,
                title=f'通知{i}',
            )

        assert Notification.get_unread_count(user) == 5

        Notification.mark_all_as_read(user)

        assert Notification.get_unread_count(user) == 0

        # read_atが設定されていることを確認
        for notification in Notification.objects.filter(user=user):
            assert notification.is_read is True
            assert notification.read_at is not None

    @pytest.mark.django_db
    def test_mark_all_as_read_only_affects_user(self, tenant, user, other_user):
        """他のユーザーの通知に影響しない"""
        Notification.objects.create(tenant=tenant, user=user, title='ユーザー通知')
        Notification.objects.create(tenant=tenant, user=other_user, title='他ユーザー通知')

        Notification.mark_all_as_read(user)

        # userの通知は既読
        assert Notification.get_unread_count(user) == 0
        # other_userの通知は未読のまま
        assert Notification.get_unread_count(other_user) == 1


# =============================================================================
# Priority Tests
# =============================================================================

class TestNotificationPriority:
    """優先度のテスト"""

    @pytest.mark.django_db
    def test_all_priorities_valid(self, tenant, user):
        """全ての優先度が有効"""
        for priority_value, _ in NotificationPriorityChoices.choices:
            notification = Notification.objects.create(
                tenant=tenant,
                user=user,
                title='優先度テスト',
                priority=priority_value,
            )
            assert notification.priority == priority_value
