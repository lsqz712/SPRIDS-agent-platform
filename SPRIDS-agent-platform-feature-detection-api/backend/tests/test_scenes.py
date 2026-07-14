"""
检测场景接口测试
测试目标：
  - 场景列表：正常返回、按分类筛选
  - 创建场景：正常创建、重复名称、参数验证
  - 单场景详情：存在/不存在
  - 更新/删除场景
测试策略：
  - 每个测试用例独立，使用唯一场景名避免冲突
"""
import pytest


class TestListScenes:
    """场景列表测试"""

    def test_list_scenes_empty(self, client):
        """初始状态返回空列表"""
        response = client.get("/api/scenes")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"]["items"], list)

    def test_list_scenes_after_create(self, client):
        """创建场景后列表包含新场景"""
        # 先创建一个场景
        client.post(
            "/api/scenes",
            json={
                "name": "test_list_scene",
                "display_name": "测试场景列表",
                "category": "industry",
                "class_names": ["defect_a", "defect_b"],
            },
        )
        response = client.get("/api/scenes")
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["data"]["items"]]
        assert "test_list_scene" in names


class TestCreateScene:
    """创建场景测试"""

    def test_create_success(self, client):
        """正常创建场景"""
        response = client.post(
            "/api/scenes",
            json={
                "name": "create_test_scene",
                "display_name": "创建测试场景",
                "category": "industry",
                "class_names": ["short", "open"],
                "class_names_cn": {"short": "短路", "open": "开路"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "create_test_scene"
        assert data["category"] == "industry"
        assert "short" in data["class_names"]
        assert data["class_names_cn"]["short"] == "短路"

    def test_create_duplicate_name(self, client):
        """重复名称创建失败"""
        client.post(
            "/api/scenes",
            json={
                "name": "dup_scene",
                "display_name": "重复场景",
                "category": "industry",
                "class_names": ["a"],
            },
        )
        response = client.post(
            "/api/scenes",
            json={
                "name": "dup_scene",
                "display_name": "重复场景",
                "category": "industry",
                "class_names": ["a"],
            },
        )
        assert response.status_code == 400

    def test_create_missing_fields(self, client):
        """缺少必填字段"""
        response = client.post(
            "/api/scenes",
            json={"name": "missing_fields"},
        )
        assert response.status_code == 422

    def test_create_empty_class_names(self, client):
        """空类别列表"""
        response = client.post(
            "/api/scenes",
            json={
                "name": "empty_class_scene",
                "display_name": "空类别",
                "category": "industry",
                "class_names": [],
            },
        )
        assert response.status_code == 422


class TestGetScene:
    """单场景详情测试"""

    def test_get_scene_success(self, client):
        """获取存在的场景"""
        # 先创建
        resp = client.post(
            "/api/scenes",
            json={
                "name": "get_test_scene",
                "display_name": "获取测试",
                "category": "industry",
                "class_names": ["a", "b"],
            },
        )
        scene_id = resp.json()["id"]

        # 获取详情
        response = client.get(f"/api/scenes/{scene_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "get_test_scene"
        assert "default_model" in data["data"]

    def test_get_scene_not_found(self, client):
        """获取不存在的场景"""
        response = client.get("/api/scenes/99999")
        assert response.status_code == 404


class TestUpdateScene:
    """更新场景测试"""

    def test_update_success(self, client):
        """正常更新场景"""
        resp = client.post(
            "/api/scenes",
            json={
                "name": "update_test_scene",
                "display_name": "更新前",
                "category": "industry",
                "class_names": ["a"],
            },
        )
        scene_id = resp.json()["id"]

        response = client.put(
            f"/api/scenes/{scene_id}",
            json={"display_name": "更新后", "is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["data"]["display_name"] == "更新后"
        assert response.json()["data"]["is_active"] is False

    def test_update_not_found(self, client):
        """更新不存在的场景"""
        response = client.put(
            "/api/scenes/99999",
            json={"display_name": "不存在"},
        )
        assert response.status_code == 404


class TestDeleteScene:
    """删除场景测试"""

    def test_delete_success(self, client):
        """正常删除场景"""
        resp = client.post(
            "/api/scenes",
            json={
                "name": "delete_test_scene",
                "display_name": "待删除",
                "category": "industry",
                "class_names": ["a"],
            },
        )
        scene_id = resp.json()["id"]

        response = client.delete(f"/api/scenes/{scene_id}")
        assert response.status_code == 204

    def test_delete_not_found(self, client):
        """删除不存在的场景"""
        response = client.delete("/api/scenes/99999")
        assert response.status_code == 404
