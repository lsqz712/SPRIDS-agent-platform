"""
检测统计接口测试
测试目标：
  - 总览统计
  - 每日检测趋势
  - 缺陷类型分布
  - 各场景检测次数
"""
import io


class TestOverviewStatistics:
    """总览统计测试"""

    def test_overview_success(self, client, auth_headers):
        """获取总览统计"""
        response = client.get("/api/statistics/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        overview = data["data"]
        # 验证所有字段存在
        assert "total_tasks" in overview
        assert "completed_tasks" in overview
        assert "failed_tasks" in overview
        assert "total_images" in overview
        assert "total_objects" in overview
        assert "avg_inference_time_ms" in overview
        assert "class_distribution" in overview
        assert "review_distribution" in overview
        assert "severity_distribution" in overview
        assert "scene_distribution" in overview

    def test_overview_without_auth(self, client):
        """未认证访问统计"""
        response = client.get("/api/statistics/overview")
        assert response.status_code == 401


class TestDailyTrend:
    """每日趋势测试"""

    def test_daily_trend_success(self, client, auth_headers):
        """获取每日趋势"""
        response = client.get(
            "/api/statistics/daily-trend?days=7", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["days"] == 7
        assert isinstance(data["data"]["items"], list)

    def test_daily_trend_custom_days(self, client, auth_headers):
        """自定义天数"""
        response = client.get(
            "/api/statistics/daily-trend?days=30", headers=auth_headers
        )
        assert response.status_code == 200

    def test_daily_trend_invalid_days(self, client, auth_headers):
        """超范围天数"""
        response = client.get(
            "/api/statistics/daily-trend?days=400", headers=auth_headers
        )
        assert response.status_code == 422


class TestDefectDistribution:
    """缺陷分布测试"""

    def test_defect_distribution_success(self, client, auth_headers):
        """获取缺陷分布"""
        response = client.get(
            "/api/statistics/defect-distribution", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["items"], list)


class TestSceneDistribution:
    """场景分布测试"""

    def test_scene_distribution_success(self, client, auth_headers):
        """获取场景分布"""
        response = client.get(
            "/api/statistics/scene-distribution", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data["data"]
        assert isinstance(data["data"]["items"], list)
