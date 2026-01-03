"""
Django ATS パフォーマンステスト
Locustを使用した負荷テスト

実行方法:
    locust -f locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events
import random
import string


def random_email():
    """ランダムなメールアドレスを生成"""
    chars = string.ascii_lowercase + string.digits
    name = ''.join(random.choice(chars) for _ in range(10))
    return f'{name}@example.com'


class ATSUser(HttpUser):
    """ATS通常ユーザーの負荷テスト"""

    wait_time = between(1, 3)  # リクエスト間の待機時間

    def on_start(self):
        """テスト開始時のログイン"""
        # CSRFトークン取得
        response = self.client.get('/accounts/login/')
        # ログイン（テスト用ユーザー）
        self.client.post('/accounts/login/', {
            'login': 'admin@example.com',
            'password': 'admin123',
        })

    @task(10)
    def view_dashboard(self):
        """ダッシュボード閲覧"""
        self.client.get('/dashboard/')

    @task(8)
    def view_candidate_list(self):
        """候補者一覧閲覧"""
        self.client.get('/candidates/')

    @task(5)
    def search_candidates(self):
        """候補者検索"""
        queries = ['テスト', '東京', 'エンジニア', 'Python', '営業']
        query = random.choice(queries)
        self.client.get(f'/candidates/?q={query}')

    @task(5)
    def view_job_list(self):
        """求人一覧閲覧"""
        self.client.get('/jobs/')

    @task(3)
    def view_application_list(self):
        """応募一覧閲覧"""
        self.client.get('/applications/')

    @task(3)
    def view_interview_list(self):
        """面接一覧閲覧"""
        self.client.get('/interviews/')

    @task(2)
    def view_settings(self):
        """設定画面閲覧"""
        self.client.get('/settings/')

    @task(2)
    def view_reports(self):
        """レポート画面閲覧"""
        self.client.get('/reports/')


class ATSAdminUser(HttpUser):
    """ATS管理者ユーザーの負荷テスト"""

    wait_time = between(2, 5)
    weight = 1  # 通常ユーザーより少なく

    def on_start(self):
        """テスト開始時のログイン"""
        response = self.client.get('/accounts/login/')
        self.client.post('/accounts/login/', {
            'login': 'admin@example.com',
            'password': 'admin123',
        })

    @task(5)
    def view_all_candidates(self):
        """全候補者閲覧"""
        self.client.get('/candidates/')

    @task(3)
    def view_candidate_detail(self):
        """候補者詳細閲覧（ランダムID）"""
        # 実際のテストでは有効なIDを使用
        self.client.get('/candidates/')

    @task(2)
    def view_settings_status(self):
        """ステータス設定閲覧"""
        self.client.get('/settings/status/')

    @task(2)
    def view_settings_sources(self):
        """応募経路設定閲覧"""
        self.client.get('/settings/sources/')

    @task(1)
    def view_agent_list(self):
        """エージェント一覧閲覧"""
        self.client.get('/agents/')

    @task(1)
    def view_persona_list(self):
        """ペルソナ一覧閲覧"""
        self.client.get('/personas/')


class ATSAPIUser(HttpUser):
    """API負荷テスト"""

    wait_time = between(0.5, 1.5)
    weight = 2

    def on_start(self):
        """API認証"""
        response = self.client.get('/accounts/login/')
        self.client.post('/accounts/login/', {
            'login': 'admin@example.com',
            'password': 'admin123',
        })

    @task(10)
    def api_candidates_list(self):
        """候補者一覧API"""
        self.client.get('/candidates/', headers={'X-Requested-With': 'XMLHttpRequest'})

    @task(8)
    def api_jobs_list(self):
        """求人一覧API"""
        self.client.get('/jobs/', headers={'X-Requested-With': 'XMLHttpRequest'})

    @task(5)
    def api_applications_list(self):
        """応募一覧API"""
        self.client.get('/applications/', headers={'X-Requested-With': 'XMLHttpRequest'})


# パフォーマンス目標
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """リクエスト監視"""
    # 500ms以上のリクエストを警告
    if response_time > 500 and exception is None:
        print(f'SLOW: {name} took {response_time:.0f}ms')
