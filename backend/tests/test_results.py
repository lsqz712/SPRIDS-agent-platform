"""
检测结果接口测试
测试目标：
  - 单条检测结果详情
  - 人工复判（review）
  - 标注缺陷严重等级
  - 获取/更新维修建议
"""
import io


class TestGetResult:
    """检测结果详情测试"""

    def test_get_result_not_found(self, client):
        """不存在的检测结果"""
        response = client.get("/api/results/99999")
        assert response.status_code == 404


class TestResultReview:
    """人工复判测试"""

    def test_review_result_not_found(self, client, auth_headers):
        """对不存在的检测结果复判"""
        response = client.put(
            "/api/results/99999/review",
            headers=auth_headers,
            json={"review_status": "pass"},
        )
        assert response.status_code == 404

    def test_review_invalid_status(self, client, auth_headers):
        """无效的复判状态"""
        response = client.put(
            "/api/results/1/review",
            headers=auth_headers,
            json={"review_status": "invalid_status"},
        )
        assert response.status_code == 422

    def test_review_without_auth(self, client):
        """未认证复判"""
        response = client.put(
            "/api/results/1/review",
            json={"review_status": "pass"},
        )
        assert response.status_code == 401


class TestResultSeverity:
    """缺陷严重等级测试"""

    def test_update_severity_not_found(self, client, auth_headers):
        """不存在的检测结果"""
        response = client.put(
            "/api/results/99999/severity",
            headers=auth_headers,
            json={"severity": "major"},
        )
        assert response.status_code == 404

    def test_update_severity_invalid_value(self, client, auth_headers):
        """无效的严重等级"""
        response = client.put(
            "/api/results/1/severity",
            headers=auth_headers,
            json={"severity": "unknown"},
        )
        assert response.status_code == 422


class TestRepairSuggestion:
    """维修建议测试"""

    def test_get_repair_suggestion_not_found(self, client):
        """不存在的检测结果"""
        response = client.get("/api/results/99999/repair-suggestion")
        assert response.status_code == 404

    def test_update_repair_suggestion_not_found(self, client, auth_headers):
        """不存在的检测结果"""
        response = client.put(
            "/api/results/99999/repair-suggestion",
            headers=auth_headers,
            json={"repair_suggestion": "需要更换元件"},
        )
        assert response.status_code == 404

    def test_update_repair_suggestion_without_auth(self, client):
        """未认证更新"""
        response = client.put(
            "/api/results/1/repair-suggestion",
            json={"repair_suggestion": "测试"},
        )
        assert response.status_code == 401
