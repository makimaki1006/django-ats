# -*- coding: utf-8 -*-
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.accounts.models import CustomUser
from apps.tenants.models import Tenant
from apps.candidates.models import Candidate
from apps.jobs.models import Job
from apps.applications.models import Application
from apps.interviews.models import Interview
from datetime import timedelta
from django.utils import timezone

tenant = Tenant.objects.get(name='Test Company')
user = CustomUser.objects.get(email='test@example.com')

# 候補者作成
candidates = []
candidate_data = [
    ('Taro', 'Tanaka', 'active'),
    ('Hanako', 'Yamada', 'active'),
    ('Jiro', 'Sato', 'inactive'),
    ('Saburo', 'Suzuki', 'active'),
    ('Misaki', 'Takahashi', 'blacklisted'),
]
for i, (first, last, status) in enumerate(candidate_data):
    c, created = Candidate.objects.get_or_create(
        tenant=tenant,
        email=f'candidate{i}@example.com',
        defaults={
            'first_name': first,
            'last_name': last,
            'phone': f'090-1234-{i:04d}',
            'status': status,
        }
    )
    candidates.append(c)
    if created:
        print(f'Created candidate: {first} {last}')

# 求人作成
jobs = []
job_data = [
    ('Python Engineer', 'published'),
    ('Frontend Engineer', 'published'),
    ('Data Scientist', 'draft'),
    ('Project Manager', 'closed'),
]
for i, (title, status) in enumerate(job_data):
    j, created = Job.objects.get_or_create(
        tenant=tenant,
        title=title,
        defaults={
            'description': f'Job description for {title}',
            'status': status,
            'employment_type': 'full_time',
            'location': 'Tokyo',
        }
    )
    jobs.append(j)
    if created:
        print(f'Created job: {title}')

# 応募作成
statuses = ['new', 'screening', 'interview', 'offered', 'hired', 'rejected']
for i, (c, j) in enumerate(zip(candidates[:4], jobs[:4])):
    app, created = Application.objects.get_or_create(
        tenant=tenant,
        candidate=c,
        job=j,
        defaults={
            'status': statuses[i % len(statuses)],
        }
    )
    if created:
        print(f'Created application: {c.first_name} -> {j.title} ({statuses[i % len(statuses)]})')

# 面接作成
interview_statuses = ['scheduled', 'completed', 'cancelled', 'no_show']
for i, status in enumerate(interview_statuses):
    if i < len(candidates) and i < len(jobs):
        app = Application.objects.filter(tenant=tenant, candidate=candidates[i]).first()
        if app:
            interview, created = Interview.objects.get_or_create(
                tenant=tenant,
                application=app,
                defaults={
                    'interview_type': 'first',
                    'status': status,
                    'scheduled_at': timezone.now() + timedelta(days=i),
                    'interviewer': user,
                }
            )
            if created:
                print(f'Created interview: {status}')

print('Test data created successfully!')
