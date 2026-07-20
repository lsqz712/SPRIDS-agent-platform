"""
检测场景接口测试
测试目标：
  - 场景列表：正常返回、按分类筛选
  - 创建场景：正常创建、重复名称、参数验证
  - 单场景详情：存在/不存在
测试策略：
  - 每个测试用例独立，使用唯一场景名避免冲突
  - 需先注册获取 token 访问受保护接口
"""
import pytest


@pytest.fixture
def auth_token(client):
    """注册用户并返回有效的 JWT token"""
    client.post(
        "/api/auth/register",
        json={
            "username": "scene_test_user",
            "email": "scene_test@example.com",
            "password": "123456",
        },
    )
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "scene_test_user", "password": "123456"},
    )
    return login_resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


class TestListScenes:
    """场景列表测试"""

    def test_list_scenes_empty(self, client, auth_headers):
        """初始状态返回空列表"""
        response = client.get("/api/scenes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_scenes_after_create(self, client, auth_headers):
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
            headers=auth_headers,
        )
        response = client.get("/api/scenes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data]
        assert "test_list_scene" in names


class TestCreateScene:
    """创建场景测试"""

    def test_create_success(self, client, auth_headers):
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
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "create_test_scene"
        assert data["category"] == "industry"
        assert "short" in data["class_names"]
        assert data["class_names_cn"]["short"] == "短路"

    def test_create_duplicate_name(self, client, auth_headers):
        """重复名称创建失败"""
        client.post(
            "/api/scenes",
            json={
                "name": "dup_scene",
                "display_name": "重复场景",
                "category": "industry",
                "class_names": ["a"],
            },
            headers=auth_headers,
        )
        response = client.post(
            "/api/scenes",
            json={
                "name": "dup_scene",
                "display_name": "重复场景",
                "category": "industry",
                "class_names": ["a"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_create_missing_fields(self, client, auth_headers):
        """缺少必填字段"""
        response = client.post(
            "/api/scenes",
            json={"name": "missing_fields"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_create_empty_class_names(self, client, auth_headers):
        """空类别列表（后端允许空列表，返回 201）"""
        response = client.post(
            "/api/scenes",
            json={
                "name": "empty_class_scene",
                "display_name": "空类别",
                "category": "industry",
                "class_names": [],
            },
            headers=auth_headers,
        )
        # class_names 没有 min_length 限制，允许空列表
        assert response.status_code == 201
        data = response.json()
        assert data["class_names"] == []


class TestGetScene:
    """单场景详情测试"""

    def test_get_scene_success(self, client, auth_headers):
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
            headers=auth_headers,
        )
        scene_id = resp.json()["id"]

        # 获取详情
        response = client.get(f"/api/scenes/{scene_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "get_test_scene"
        assert "default_model" in data

    def test_get_scene_not_found(self, client, auth_headers):
        """获取不存在的场景"""
        response = client.get("/api/scenes/99999", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateScene:
    """更新场景测试（暂无可用的 PUT/PATCH 路由，跳过）"""

    def test_update_scene_not_supported(self, client, auth_headers):
        """更新场景路由不存在"""
        resp = client.post(
            "/api/scenes",
            json={
                "name": "update_skip_scene",
                "display_name": "更新跳过",
                "category": "industry",
                "class_names": ["a"],
            },
            headers=auth_headers,
        )
        scene_id = resp.json()["id"]

        response = client.put(
            f"/api/scenes/{scene_id}",
            json={"display_name": "更新后"},
            headers=auth_headers,
        )
        assert response.status_code == 405


class TestDeleteScene:
    """删除场景测试（暂无可用的 DELETE 路由，跳过）"""

    def test_delete_scene_not_supported(self, client, auth_headers):
        """删除场景路由不存在"""
        response = client.delete("/api/scenes/99999", headers=auth_headers)
        assert response.status_code == 405
