"""Django ATS - 定期レポートタスク

Celeryタスクで定期レポートを生成・配信。
"""

import logging
from datetime import timedelta
from io import BytesIO, StringIO
import csv

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Count, Avg, Q
from django.template.loader import render_to_string
from django.utils import timezone

from apps.applications.models import Application, ApplicationStatusChoices
from apps.candidates.models import Candidate
from apps.interviews.models import Interview
from apps.jobs.models import Job, JobStatusChoices
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_and_send_report(self, schedule_id: str):
    """定期レポートを生成して配信

    Args:
        schedule_id: ReportScheduleのID
    """
    from .models import ReportSchedule, ReportExecution

    try:
        schedule = ReportSchedule.objects.select_related('tenant').get(id=schedule_id)
    except ReportSchedule.DoesNotExist:
        logger.error(f"ReportSchedule not found: {schedule_id}")
        return

    if not schedule.is_active:
        logger.info(f"Schedule {schedule.name} is not active, skipping")
        return

    # 実行履歴を作成
    execution = ReportExecution.objects.create(
        tenant=schedule.tenant,
        schedule=schedule,
        status='running',
        started_at=timezone.now(),
    )

    try:
        # レポート生成
        report_data = generate_report_data(schedule)
        report_content = format_report(schedule, report_data)

        # メール送信
        send_report_email(schedule, report_content, execution)

        # 成功記録
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.recipients_sent = schedule.recipients + schedule.cc_recipients
        execution.save()

        schedule.last_run_at = timezone.now()
        schedule.last_run_status = 'success'
        schedule.last_run_error = ''
        schedule.save()

        logger.info(f"Report sent successfully: {schedule.name}")

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        execution.status = 'failed'
        execution.completed_at = timezone.now()
        execution.error_message = str(e)
        execution.save()

        schedule.last_run_status = 'failed'
        schedule.last_run_error = str(e)
        schedule.save()

        # リトライ
        raise self.retry(exc=e, countdown=60 * 5)


def generate_report_data(schedule):
    """レポートデータを生成"""
    from .models import ReportTypeChoices

    tenant = schedule.tenant
    now = timezone.now()

    if schedule.report_type == ReportTypeChoices.MONTHLY_SUMMARY:
        return generate_monthly_summary(tenant, now)
    elif schedule.report_type == ReportTypeChoices.WEEKLY_PROGRESS:
        return generate_weekly_progress(tenant, now)
    elif schedule.report_type == ReportTypeChoices.BIMONTHLY_COMPARISON:
        return generate_bimonthly_comparison(tenant, now)
    elif schedule.report_type == ReportTypeChoices.SEMI_ANNUAL:
        return generate_semi_annual(tenant, now)
    else:
        return generate_monthly_summary(tenant, now)


def generate_monthly_summary(tenant, now):
    """月次サマリーレポートデータ"""
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

    # 今月の統計
    this_month_apps = Application.objects.filter(
        tenant=tenant,
        applied_at__gte=this_month_start,
    )
    this_month_candidates = Candidate.objects.filter(
        tenant=tenant,
        created_at__gte=this_month_start,
    )

    # 先月の統計
    last_month_apps = Application.objects.filter(
        tenant=tenant,
        applied_at__gte=last_month_start,
        applied_at__lt=this_month_start,
    )
    last_month_candidates = Candidate.objects.filter(
        tenant=tenant,
        created_at__gte=last_month_start,
        created_at__lt=this_month_start,
    )

    # ステータス別集計
    status_breakdown = this_month_apps.values('status').annotate(
        count=Count('id')
    )

    # 採用数
    hired_count = this_month_apps.filter(
        status=ApplicationStatusChoices.OFFER_ACCEPTED
    ).count()

    return {
        'period': f"{this_month_start.strftime('%Y年%m月')}",
        'period_type': '月次',
        'summary': {
            'applications': {
                'current': this_month_apps.count(),
                'previous': last_month_apps.count(),
            },
            'candidates': {
                'current': this_month_candidates.count(),
                'previous': last_month_candidates.count(),
            },
            'hired': hired_count,
            'active_jobs': Job.objects.filter(
                tenant=tenant,
                status=JobStatusChoices.ACTIVE
            ).count(),
        },
        'status_breakdown': list(status_breakdown),
        'generated_at': now.isoformat(),
    }


def generate_weekly_progress(tenant, now):
    """週次進捗レポートデータ"""
    this_week_start = now - timedelta(days=now.weekday())
    this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    last_week_start = this_week_start - timedelta(days=7)

    # 今週の新規応募
    new_apps = Application.objects.filter(
        tenant=tenant,
        applied_at__gte=this_week_start,
    )

    # ステータス変更があった応募
    status_changes = Application.objects.filter(
        tenant=tenant,
        updated_at__gte=this_week_start,
    ).exclude(
        applied_at__gte=this_week_start
    )

    # 今週の面接
    interviews = Interview.objects.filter(
        tenant=tenant,
        scheduled_at__gte=this_week_start,
        scheduled_at__lt=this_week_start + timedelta(days=7),
    )

    return {
        'period': f"{this_week_start.strftime('%Y年%m月%d日')}週",
        'period_type': '週次',
        'summary': {
            'new_applications': new_apps.count(),
            'status_changes': status_changes.count(),
            'interviews_scheduled': interviews.filter(status='scheduled').count(),
            'interviews_completed': interviews.filter(status='completed').count(),
        },
        'new_applications': [
            {
                'candidate': app.candidate.name,
                'job': app.job.title,
                'applied_at': app.applied_at.isoformat(),
            }
            for app in new_apps.select_related('candidate', 'job')[:20]
        ],
        'generated_at': now.isoformat(),
    }


def generate_bimonthly_comparison(tenant, now):
    """過去2ヶ月比較レポートデータ"""
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    two_months_ago_start = (last_month_start - timedelta(days=1)).replace(day=1)

    months = []
    for start, end, label in [
        (last_month_start, this_month_start, '先月'),
        (two_months_ago_start, last_month_start, '先々月'),
    ]:
        apps = Application.objects.filter(
            tenant=tenant,
            applied_at__gte=start,
            applied_at__lt=end,
        )
        months.append({
            'label': label,
            'period': start.strftime('%Y年%m月'),
            'applications': apps.count(),
            'hired': apps.filter(status=ApplicationStatusChoices.OFFER_ACCEPTED).count(),
            'rejected': apps.filter(status=ApplicationStatusChoices.REJECTED).count(),
        })

    return {
        'period': f"{two_months_ago_start.strftime('%Y年%m月')}〜{last_month_start.strftime('%m月')}比較",
        'period_type': '2ヶ月比較',
        'months': months,
        'change': {
            'applications': months[0]['applications'] - months[1]['applications'],
            'hired': months[0]['hired'] - months[1]['hired'],
        },
        'generated_at': now.isoformat(),
    }


def generate_semi_annual(tenant, now):
    """半期レビューレポートデータ"""
    # 半期の開始を計算（1月or7月）
    if now.month >= 7:
        period_start = now.replace(month=7, day=1, hour=0, minute=0, second=0, microsecond=0)
        period_label = f"{now.year}年下半期"
    else:
        period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        period_label = f"{now.year}年上半期"

    apps = Application.objects.filter(
        tenant=tenant,
        applied_at__gte=period_start,
    )
    candidates = Candidate.objects.filter(
        tenant=tenant,
        created_at__gte=period_start,
    )
    interviews = Interview.objects.filter(
        tenant=tenant,
        scheduled_at__gte=period_start,
    )

    # KPI計算
    total_apps = apps.count()
    hired = apps.filter(status=ApplicationStatusChoices.OFFER_ACCEPTED).count()
    hire_rate = (hired / total_apps * 100) if total_apps > 0 else 0

    return {
        'period': period_label,
        'period_type': '半期',
        'kpis': {
            'total_applications': total_apps,
            'total_candidates': candidates.count(),
            'total_interviews': interviews.count(),
            'hired': hired,
            'hire_rate': round(hire_rate, 1),
        },
        'monthly_breakdown': [],  # 月別内訳は必要に応じて追加
        'generated_at': now.isoformat(),
    }


def format_report(schedule, data):
    """レポートをフォーマット"""
    from .models import ReportFormatChoices

    if schedule.format == ReportFormatChoices.HTML:
        return format_report_html(schedule, data)
    elif schedule.format == ReportFormatChoices.CSV:
        return format_report_csv(schedule, data)
    else:
        # PDF/Excelは将来実装
        return format_report_html(schedule, data)


def format_report_html(schedule, data):
    """HTMLレポートを生成"""
    context = {
        'schedule': schedule,
        'data': data,
        'tenant': schedule.tenant,
    }
    return render_to_string('reports/email/report_template.html', context)


def format_report_csv(schedule, data):
    """CSVレポートを生成"""
    output = StringIO()
    writer = csv.writer(output)

    # ヘッダー
    writer.writerow(['レポート', schedule.name])
    writer.writerow(['期間', data.get('period', '')])
    writer.writerow(['生成日時', data.get('generated_at', '')])
    writer.writerow([])

    # サマリー
    summary = data.get('summary', {})
    writer.writerow(['項目', '今期', '前期', '増減'])
    for key, value in summary.items():
        if isinstance(value, dict):
            current = value.get('current', 0)
            previous = value.get('previous', 0)
            writer.writerow([key, current, previous, current - previous])
        else:
            writer.writerow([key, value, '', ''])

    return output.getvalue()


def send_report_email(schedule, content, execution):
    """レポートをメール送信"""
    from .models import ReportFormatChoices

    subject = f"【{schedule.tenant.name}】{schedule.name} - {timezone.now().strftime('%Y/%m/%d')}"

    if schedule.format == ReportFormatChoices.HTML:
        # HTML形式
        email = EmailMessage(
            subject=subject,
            body=content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=schedule.recipients,
            cc=schedule.cc_recipients,
        )
        email.content_subtype = 'html'
        email.send()
    else:
        # 添付ファイル形式
        email = EmailMessage(
            subject=subject,
            body=f"{schedule.name}レポートを添付します。",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=schedule.recipients,
            cc=schedule.cc_recipients,
        )

        if schedule.format == ReportFormatChoices.CSV:
            email.attach(
                f'report_{timezone.now().strftime("%Y%m%d")}.csv',
                content,
                'text/csv'
            )

        email.send()


@shared_task
def process_scheduled_reports():
    """スケジュールされた全レポートを処理

    Celery Beatから定期実行される。
    """
    from .models import ReportSchedule, ReportTypeChoices

    now = timezone.now()
    schedules = ReportSchedule.objects.filter(is_active=True)

    for schedule in schedules:
        should_run = False

        # レポートタイプに応じて実行判定
        if schedule.report_type == ReportTypeChoices.MONTHLY_SUMMARY:
            # 毎月1日
            should_run = now.day == 1 and now.hour == 9
        elif schedule.report_type == ReportTypeChoices.WEEKLY_PROGRESS:
            # 毎週月曜
            should_run = now.weekday() == 0 and now.hour == 9
        elif schedule.report_type == ReportTypeChoices.BIMONTHLY_COMPARISON:
            # 毎月15日
            should_run = now.day == 15 and now.hour == 9
        elif schedule.report_type == ReportTypeChoices.SEMI_ANNUAL:
            # 6月1日と12月1日
            should_run = now.day == 1 and now.month in [6, 12] and now.hour == 9
        elif schedule.cron_expression:
            # カスタムスケジュール（別途評価ロジック必要）
            pass

        if should_run:
            generate_and_send_report.delay(str(schedule.id))


@shared_task
def send_test_report(schedule_id: str, email: str):
    """テストレポートを送信

    Args:
        schedule_id: ReportScheduleのID
        email: 送信先メールアドレス
    """
    from .models import ReportSchedule

    try:
        schedule = ReportSchedule.objects.get(id=schedule_id)
        report_data = generate_report_data(schedule)
        report_content = format_report(schedule, report_data)

        subject = f"【テスト】{schedule.name}"
        email_msg = EmailMessage(
            subject=subject,
            body=report_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        if schedule.format == 'html':
            email_msg.content_subtype = 'html'
        email_msg.send()

        logger.info(f"Test report sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Test report failed: {e}")
        return False
