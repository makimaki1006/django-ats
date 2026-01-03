"""
Django ATS - 通知ビュー

アプリ内通知の一覧表示、既読管理、削除機能を提供。
HTMXによるリアルタイム更新対応。
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views import View
from django.views.generic import ListView

from apps.core.mixins import HtmxMixin, PaginationMixin

from .models import Notification, NotificationTypeChoices, NotificationPriorityChoices


class NotificationListView(
    LoginRequiredMixin,
    PaginationMixin,
    HtmxMixin,
    ListView
):
    """通知一覧

    ユーザーの全通知を表示。
    フィルター: 未読/既読、タイプ、優先度
    """
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        queryset = Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

        # 未読/既読フィルター
        is_read = self.request.GET.get('is_read')
        if is_read == 'unread':
            queryset = queryset.filter(is_read=False)
        elif is_read == 'read':
            queryset = queryset.filter(is_read=True)

        # タイプフィルター
        notification_type = self.request.GET.get('type')
        if notification_type and notification_type in dict(NotificationTypeChoices.choices):
            queryset = queryset.filter(notification_type=notification_type)

        # 優先度フィルター
        priority = self.request.GET.get('priority')
        if priority and priority in dict(NotificationPriorityChoices.choices):
            queryset = queryset.filter(priority=priority)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.get_unread_count(self.request.user)
        context['notification_types'] = NotificationTypeChoices.choices
        context['priority_choices'] = NotificationPriorityChoices.choices
        context['current_filter'] = self.request.GET.get('is_read', 'all')
        context['current_type'] = self.request.GET.get('type', '')
        context['current_priority'] = self.request.GET.get('priority', '')
        return context


class NotificationDropdownView(LoginRequiredMixin, View):
    """ヘッダー通知ドロップダウン（HTMX）

    最新5件の未読通知を表示するドロップダウン用パーシャル。
    """

    def get(self, request):
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:5]

        unread_count = Notification.get_unread_count(request.user)

        return TemplateResponse(
            request,
            'notifications/partials/dropdown.html',
            {
                'notifications': notifications,
                'unread_count': unread_count,
            }
        )


class NotificationUnreadCountView(LoginRequiredMixin, View):
    """未読数バッジ（HTMX）

    ヘッダーのベルアイコンに表示する未読数を返す。
    """

    def get(self, request):
        count = Notification.get_unread_count(request.user)
        if count > 0:
            # 99+表示
            display = '99+' if count > 99 else str(count)
            return HttpResponse(
                f'<span class="absolute -top-1 -right-1 h-5 w-5 flex items-center '
                f'justify-center rounded-full bg-red-500 text-xs text-white">'
                f'{display}</span>'
            )
        return HttpResponse('')


class NotificationMarkReadView(LoginRequiredMixin, View):
    """通知を既読にする（HTMX）"""

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            user=request.user
        )
        notification.mark_as_read()

        # HTMXリクエストの場合はパーシャルを返す
        if request.headers.get('HX-Request'):
            return TemplateResponse(
                request,
                'notifications/partials/notification_row.html',
                {'notification': notification}
            )

        return HttpResponse(status=204)


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    """全通知を既読にする（HTMX）"""

    def post(self, request):
        Notification.mark_all_as_read(request.user)

        # HTMXリクエストの場合はリダイレクト指示
        if request.headers.get('HX-Request'):
            response = HttpResponse()
            response['HX-Redirect'] = request.META.get('HTTP_REFERER', '/notifications/')
            return response

        return HttpResponse(status=204)


class NotificationDeleteView(LoginRequiredMixin, View):
    """通知を削除する（HTMX）"""

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            user=request.user
        )
        notification.delete()

        # HTMXリクエストの場合は空を返す（行が消える）
        if request.headers.get('HX-Request'):
            return HttpResponse('')

        return HttpResponse(status=204)


class NotificationClearAllView(LoginRequiredMixin, View):
    """全通知を削除する"""

    def post(self, request):
        Notification.objects.filter(user=request.user).delete()

        # HTMXリクエストの場合はリダイレクト指示
        if request.headers.get('HX-Request'):
            response = HttpResponse()
            response['HX-Redirect'] = '/notifications/'
            return response

        return HttpResponse(status=204)
