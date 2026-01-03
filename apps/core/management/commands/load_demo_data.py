# -*- coding: utf-8 -*-
"""
デモデータインポートコマンド

使用方法:
    python manage.py load_demo_data --pattern kaigo
    python manage.py load_demo_data --pattern iryo
    python manage.py load_demo_data --pattern shogai
"""

import csv
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser
from apps.candidates.models import Candidate
from apps.jobs.models import Job, JobPersona
from apps.applications.models import Application
from apps.interviews.models import Interview
from apps.personas.models import Persona
from apps.agents.models import AgentCompany


class Command(BaseCommand):
    help = 'CSVファイルからデモデータをインポートします'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pattern',
            type=str,
            choices=['kaigo', 'iryo', 'shogai'],
            required=True,
            help='インポートするパターン (kaigo=介護, iryo=医療, shogai=障害福祉)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='インポート前に既存データを削除'
        )

    def handle(self, *args, **options):
        pattern = options['pattern']
        clear = options['clear']

        # データディレクトリのパス
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        data_dir = base_dir / 'demo_data' / 'spreadsheet' / pattern

        if not data_dir.exists():
            raise CommandError(f'データディレクトリが見つかりません: {data_dir}')

        self.stdout.write(f'パターン: {pattern}')
        self.stdout.write(f'データディレクトリ: {data_dir}')

        try:
            with transaction.atomic():
                # テナント作成/取得
                tenant = self._get_or_create_tenant(data_dir, pattern)

                if clear:
                    self._clear_data(tenant)
                    self.stdout.write(self.style.WARNING('既存データを削除しました'))

                # データインポート
                self._import_candidates(data_dir, tenant)
                self._import_jobs(data_dir, tenant)
                self._import_applications(data_dir, tenant)
                self._import_interviews(data_dir, tenant)

            self.stdout.write(self.style.SUCCESS('デモデータのインポートが完了しました'))

        except Exception as e:
            raise CommandError(f'インポートエラー: {e}')

    def _get_or_create_tenant(self, data_dir, pattern):
        """テナントを作成または取得"""
        settings_file = data_dir / 'settings.csv'
        settings = {}

        with open(settings_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                settings[row['key']] = row['value']

        tenant_code = settings.get('tenant_code', pattern)
        company_name = settings.get('company_name', f'テスト会社_{pattern}')

        tenant, created = Tenant.objects.get_or_create(
            code=tenant_code,
            defaults={
                'name': company_name,
                'is_active': True,
            }
        )

        if created:
            self.stdout.write(f'テナント作成: {company_name} ({tenant_code})')
        else:
            self.stdout.write(f'既存テナント使用: {company_name} ({tenant_code})')

        # 管理ユーザー作成
        admin_user, _ = CustomUser.objects.get_or_create(
            email=f'admin@{tenant_code}.example.com',
            defaults={
                'tenant': tenant,
                'is_staff': True,
                'is_active': True,
            }
        )

        self.admin_user = admin_user
        return tenant

    def _clear_data(self, tenant):
        """テナントのデータを削除"""
        Interview.objects.filter(application__candidate__tenant=tenant).delete()
        Application.objects.filter(candidate__tenant=tenant).delete()
        JobPersona.objects.filter(job__tenant=tenant).delete()
        Job.objects.filter(tenant=tenant).delete()
        Candidate.objects.filter(tenant=tenant).delete()
        Persona.objects.filter(tenant=tenant).delete()
        AgentCompany.objects.filter(tenant=tenant).delete()

    def _parse_datetime(self, dt_str):
        """ISO 8601形式の日時をパース"""
        if not dt_str:
            return None
        try:
            # +09:00 形式のタイムゾーンを処理
            dt_str = dt_str.replace('+09:00', '+0900')
            return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S%z')
        except ValueError:
            try:
                return datetime.strptime(dt_str, '%Y-%m-%d')
            except ValueError:
                return None

    def _import_candidates(self, data_dir, tenant):
        """候補者データをインポート"""
        csv_file = data_dir / 'candidates.csv'
        if not csv_file.exists():
            self.stdout.write(self.style.WARNING('candidates.csv が見つかりません'))
            return

        count = 0
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Candidate.objects.update_or_create(
                    tenant=tenant,
                    email=row['email'],
                    defaults={
                        'name': row['name'],
                        'name_kana': row.get('name_kana', ''),
                        'phone': row.get('phone', ''),
                        'birth_date': self._parse_datetime(row.get('birth_date')),
                        'gender': row.get('gender', ''),
                        'postal_code': row.get('postal_code', ''),
                        'address': row.get('address', ''),
                        'current_company': row.get('current_company', ''),
                        'current_position': row.get('current_position', ''),
                        'years_of_experience': int(row['years_of_experience']) if row.get('years_of_experience') else 0,
                        'desired_salary_min': int(row['desired_salary_min']) if row.get('desired_salary_min') else None,
                        'desired_salary_max': int(row['desired_salary_max']) if row.get('desired_salary_max') else None,
                        'status': row.get('status', 'new'),
                        'source': row.get('source', ''),
                        'notes': row.get('notes', ''),
                        'registered_by': self.admin_user,
                    }
                )
                count += 1

        self.stdout.write(f'候補者: {count}件インポート')

    def _import_jobs(self, data_dir, tenant):
        """求人データをインポート"""
        csv_file = data_dir / 'jobs.csv'
        if not csv_file.exists():
            self.stdout.write(self.style.WARNING('jobs.csv が見つかりません'))
            return

        count = 0
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                Job.objects.update_or_create(
                    tenant=tenant,
                    unique_code=row['id'][:20],  # IDの一部を使用
                    defaults={
                        'title': row['title'],
                        'department': row.get('department', ''),
                        'employment_type': row.get('employment_type', 'full_time'),
                        'location': row.get('work_location', ''),
                        'salary_min': int(row['salary_min']) if row.get('salary_min') else None,
                        'salary_max': int(row['salary_max']) if row.get('salary_max') else None,
                        'description': row.get('description', ''),
                        'requirements': row.get('requirements', ''),
                        'preferred_requirements': row.get('preferred_skills', ''),
                        'benefits': row.get('benefits', ''),
                        'headcount': int(row['number_of_positions']) if row.get('number_of_positions') else 1,
                        'status': row.get('status', 'draft'),
                        'notes': row.get('notes', ''),
                        'created_by': self.admin_user,
                    }
                )
                count += 1

        self.stdout.write(f'求人: {count}件インポート')

    def _import_applications(self, data_dir, tenant):
        """応募データをインポート"""
        csv_file = data_dir / 'applications.csv'
        if not csv_file.exists():
            self.stdout.write(self.style.WARNING('applications.csv が見つかりません'))
            return

        # 候補者と求人のマッピングを作成
        candidates = {c.email: c for c in Candidate.objects.filter(tenant=tenant)}
        jobs = {j.unique_code: j for j in Job.objects.filter(tenant=tenant)}

        count = 0
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 候補者名からメールを推測（簡易マッチング）
                candidate_name = row.get('candidate_name', '')
                candidate = None
                for c in candidates.values():
                    if c.name == candidate_name:
                        candidate = c
                        break

                if not candidate:
                    continue

                # 求人IDからマッチング
                job_id = row.get('job_id', '')[:20]
                job = jobs.get(job_id)
                if not job:
                    continue

                Application.objects.update_or_create(
                    candidate=candidate,
                    job=job,
                    defaults={
                        'status': row.get('status', 'new'),
                        'source': row.get('source', ''),
                        'applied_at': self._parse_datetime(row.get('applied_at')) or timezone.now(),
                        'evaluation_score': int(row['evaluation_score']) if row.get('evaluation_score') else None,
                        'evaluation_notes': row.get('evaluation_notes', ''),
                        'notes': row.get('notes', ''),
                        'registered_by': self.admin_user,
                    }
                )
                count += 1

        self.stdout.write(f'応募: {count}件インポート')

    def _import_interviews(self, data_dir, tenant):
        """面接データをインポート"""
        csv_file = data_dir / 'interviews.csv'
        if not csv_file.exists():
            self.stdout.write(self.style.WARNING('interviews.csv が見つかりません'))
            return

        # 応募のマッピングを作成
        applications = {}
        for app in Application.objects.filter(candidate__tenant=tenant).select_related('candidate', 'job'):
            key = (app.candidate.name, app.job.title)
            applications[key] = app

        count = 0
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                candidate_name = row.get('candidate_name', '')
                job_title = row.get('job_title', '')

                application = applications.get((candidate_name, job_title))
                if not application:
                    continue

                Interview.objects.update_or_create(
                    application=application,
                    round_number=int(row.get('round_number', 1)),
                    defaults={
                        'interview_type': row.get('interview_type', 'in_person'),
                        'scheduled_at': self._parse_datetime(row.get('scheduled_at')),
                        'duration_minutes': int(row['duration_minutes']) if row.get('duration_minutes') else 60,
                        'location': row.get('location', ''),
                        'meeting_url': row.get('meeting_url', ''),
                        'status': row.get('status', 'scheduled'),
                        'result': row.get('result', '') or None,
                        'feedback': row.get('feedback', ''),
                        'score': int(row['score']) if row.get('score') else None,
                        'notes': row.get('notes', ''),
                        'created_by': self.admin_user,
                    }
                )
                count += 1

        self.stdout.write(f'面接: {count}件インポート')
