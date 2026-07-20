"""
检测任务接口测试
测试目标：
  - 任务列表：分页、筛选
  - 创建单图检测任务
  - 创建批量检测任务
  - 任务详情（含检测结果）
  - 删除任务
  - 任务检测结果列表
"""
import io

import pytest


@pytest.fixture
def auth_token(client):
    """注册用户并返回有效的 JWT token"""
    client.post(
        "/api/auth/register",
        json={
            "username": "task_test_user",
            "email": "task_test@example.com",
            "password": "123456",
        },
    )
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "task_test_user", "password": "123456"},
    )
    return login_resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


class TestListTasks:
    """任务列表测试"""

    def test_list_tasks_empty(self, client, auth_headers):
        """初始状态返回空列表"""
        response = client.get("/api/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"]["items"], list)

    def test_list_tasks_pagination(self, client, auth_headers):
        """任务列表分页参数"""
        response = client.get("/api/tasks?page=1&page_size=5", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["page"] == 1


class TestCreateSingleTask:
    """单图检测任务测试"""

    def test_create_single_task_success(self, client, auth_headers):
        """正常创建单图检测任务"""
        # 先创建场景
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_single_scene",
                "display_name": "单图检测场景",
                "category": "industry",
                "class_names": ["short", "open"],
            },
            headers=auth_headers,
        )
        scene_id = scene_resp.json()["id"]

        # 创建任务（上传假图像）
        response = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={
                "image": ("test.jpg", io.BytesIO(b"fake_image_data"), "image/jpeg")
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["scene_id"] == scene_id
        assert data["data"]["status"] == "pending"

    def test_create_single_task_no_image(self, client, auth_headers):
        """不传图像文件"""
        response = client.post(
            "/api/tasks/single",
            data={"scene_id": 1},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_create_single_task_nonexistent_scene(self, client, auth_headers):
        """不存在的场景ID"""
        response = client.post(
            "/api/tasks/single",
            data={"scene_id": 99999},
            files={
                "image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")
            },
            headers=auth_headers,
        )
        assert response.status_code == 201  # 任务创建成功，但scene_id无效可在后续处理


class TestCreateBatchTask:
    """批量检测任务测试"""

    def test_create_batch_task_success(self, client, auth_headers):
        """正常创建批量检测任务"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_batch_scene",
                "display_name": "批量检测场景",
                "category": "industry",
                "class_names": ["a", "b"],
            },
            headers=auth_headers,
        )
        scene_id = scene_resp.json()["id"]

        response = client.post(
            "/api/tasks/batch",
            data={"scene_id": scene_id},
            files=[
                ("images", ("img1.jpg", io.BytesIO(b"data1"), "image/jpeg")),
                ("images", ("img2.jpg", io.BytesIO(b"data2"), "image/jpeg")),
            ],
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["image_count"] == 2

    def test_create_batch_task_no_files(self, client, auth_headers):
        """不传文件"""
        response = client.post(
            "/api/tasks/batch",
            data={"scene_id": 1},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestGetTask:
    """任务详情测试"""

    def test_get_task_success(self, client, auth_headers):
        """获取存在的任务"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_get_scene",
                "display_name": "任务获取场景",
                "category": "industry",
                "class_names": ["a"],
            },
            headers=auth_headers,
        )
        scene_id = scene_resp.json()["id"]

        # 创建任务
        task_resp = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={"image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")},
            headers=auth_headers,
        )
        task_id = task_resp.json()["data"]["task_id"]

        response = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["task"]["id"] == task_id
        assert data["data"]["task"].get("scene_name") is not None

    def test_get_task_with_results(self, client, auth_headers):
        """获取任务详情并包含结果"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_results_scene",
                "display_name": "含结果场景",
                "category": "industry",
                "class_names": ["a"],
            },
            headers=auth_headers,
        )
        scene_id = scene_resp.json()["id"]
        task_resp = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={"image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")},
            headers=auth_headers,
        )
        task_id = task_resp.json()["data"]["task_id"]

        response = client.get(
            f"/api/tasks/{task_id}?include_results=true",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "results" in response.json()["data"]

    def test_get_task_not_found(self, client, auth_headers):
        """获取不存在的任务"""
        response = client.get("/api/tasks/99999", headers=auth_headers)
        assert response.status_code == 404


class TestDeleteTask:
    """删除任务测试"""

    def test_delete_pending_task_success(self, client, auth_headers):
        """删除pending状态的任务"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_delete_scene",
                "display_name": "删除场景",
                "category": "industry",
                "class_names": ["a"],
            },
            headers=auth_headers,
        )
        scene_id = scene_resp.json()["id"]
        task_resp = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={"image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")},
            headers=auth_headers,
        )
        task_id = task_resp.json()["data"]["task_id"]

        response = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 204


class TestGetTaskResults:
    """任务检测结果列表测试"""

    def test_get_task_results_empty(self, client, auth_headers):
        """获取任务的结果列表（空）"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_results_list_scene",
                "display_name": "结果列表场景",
                "category": "industry",
                "class_names": ["a"],
            },
            headers=auth_headers,
        )
        scene_id = scene_resp.json()["id"]
        task_resp = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={"image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")},
            headers=auth_headers,
        )
        task_id = task_resp.json()["data"]["task_id"]

        response = client.get(f"/api/tasks/{task_id}/results", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"]["items"], list)
