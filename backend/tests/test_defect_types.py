"""
缺陷类型字典接口测试
测试目标：
  - 类型列表：搜索、筛选
  - 创建缺陷类型：正常创建、编码唯一性
  - 更新/删除缺陷类型
"""
import pytest


class TestListDefectTypes:
    """缺陷类型列表测试"""

    def test_list_defect_types_empty(self, client):
        """初始状态返回空列表"""
        response = client.get("/api/defect-types")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    def test_list_with_keyword(self, client):
        """按关键词搜索"""
        response = client.get("/api/defect-types?keyword=short")
        assert response.status_code == 200

    def test_list_with_severity_filter(self, client):
        """按严重等级筛选"""
        response = client.get("/api/defect-types?severity=critical")
        assert response.status_code == 200


class TestCreateDefectType:
    """创建缺陷类型测试"""

    def test_create_success(self, client, auth_headers):
        """正常创建缺陷类型"""
        response = client.post(
            "/api/defect-types",
            headers=auth_headers,
            json={
                "code": "SHORT_01",
                "name": "Short Circuit",
                "name_cn": "短路",
                "severity": "critical",
                "description": "PCB线路短路缺陷",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 201
        assert data["data"]["code"] == "SHORT_01"
        assert data["data"]["name_cn"] == "短路"

    def test_create_duplicate_code(self, client, auth_headers):
        """重复编码创建失败"""
        client.post(
            "/api/defect-types",
            headers=auth_headers,
            json={
                "code": "DUP_CODE",
                "name": "Duplicate",
                "name_cn": "重复",
                "severity": "major",
            },
        )
        response = client.post(
            "/api/defect-types",
            headers=auth_headers,
            json={
                "code": "DUP_CODE",
                "name": "Duplicate Again",
                "name_cn": "再次重复",
                "severity": "major",
            },
        )
        assert response.status_code == 400

    def test_create_invalid_severity(self, client, auth_headers):
        """无效的严重等级"""
        response = client.post(
            "/api/defect-types",
            headers=auth_headers,
            json={
                "code": "INVALID_SEV",
                "name": "Invalid",
                "name_cn": "无效",
                "severity": "unknown",
            },
        )
        assert response.status_code == 422

    def test_create_without_auth(self, client):
        """未认证创建"""
        response = client.post(
            "/api/defect-types",
            json={
                "code": "NO_AUTH",
                "name": "No Auth",
                "name_cn": "未认证",
                "severity": "minor",
            },
        )
        assert response.status_code == 401


class TestUpdateDefectType:
    """更新缺陷类型测试"""

    def test_update_success(self, client, auth_headers):
        """正常更新缺陷类型"""
        resp = client.post(
            "/api/defect-types",
            headers=auth_headers,
            json={
                "code": "UPDATE_TYPE",
                "name": "Before Update",
                "name_cn": "更新前",
                "severity": "minor",
            },
        )
        type_id = resp.json()["data"]["id"]

        response = client.put(
            f"/api/defect-types/{type_id}",
            headers=auth_headers,
            json={
                "name": "After Update",
                "name_cn": "更新后",
                "severity": "major",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "After Update"
        assert data["data"]["severity"] == "major"

    def test_update_not_found(self, client, auth_headers):
        """更新不存在的类型"""
        response = client.put(
            "/api/defect-types/99999",
            headers=auth_headers,
            json={"name": "Not Found"},
        )
        assert response.status_code == 404


class TestDeleteDefectType:
    """删除缺陷类型测试"""

    def test_delete_success(self, client, auth_headers):
        """正常删除缺陷类型"""
        resp = client.post(
            "/api/defect-types",
            headers=auth_headers,
            json={
                "code": "DELETE_TYPE",
                "name": "To Delete",
                "name_cn": "待删除",
                "severity": "minor",
            },
        )
        type_id = resp.json()["data"]["id"]

        response = client.delete(f"/api/defect-types/{type_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_delete_not_found(self, client, auth_headers):
        """删除不存在的类型"""
        response = client.delete("/api/defect-types/99999", headers=auth_headers)
        assert response.status_code == 404
