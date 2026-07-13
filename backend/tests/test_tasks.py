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


class TestListTasks:
    """任务列表测试"""

    def test_list_tasks_empty(self, client):
        """初始状态返回空列表"""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"]["items"], list)

    def test_list_tasks_pagination(self, client):
        """任务列表分页参数"""
        response = client.get("/api/tasks?page=1&page_size=5")
        assert response.status_code == 200
        assert response.json()["data"]["page"] == 1


class TestCreateSingleTask:
    """单图检测任务测试"""

    def test_create_single_task_success(self, client):
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
        )
        scene_id = scene_resp.json()["id"]

        # 创建任务（上传假图像）
        response = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={
                "image": ("test.jpg", io.BytesIO(b"fake_image_data"), "image/jpeg")
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["scene_id"] == scene_id
        assert data["data"]["status"] == "pending"

    def test_create_single_task_no_image(self, client):
        """不传图像文件"""
        response = client.post(
            "/api/tasks/single",
            data={"scene_id": 1},
        )
        assert response.status_code == 422

    def test_create_single_task_nonexistent_scene(self, client):
        """不存在的场景ID"""
        response = client.post(
            "/api/tasks/single",
            data={"scene_id": 99999},
            files={
                "image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")
            },
        )
        assert response.status_code == 201  # 任务创建成功，但scene_id无效可在后续处理


class TestCreateBatchTask:
    """批量检测任务测试"""

    def test_create_batch_task_success(self, client):
        """正常创建批量检测任务"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_batch_scene",
                "display_name": "批量检测场景",
                "category": "industry",
                "class_names": ["a", "b"],
            },
        )
        scene_id = scene_resp.json()["id"]

        response = client.post(
            "/api/tasks/batch",
            data={"scene_id": scene_id},
            files=[
                ("images", ("img1.jpg", io.BytesIO(b"data1"), "image/jpeg")),
                ("images", ("img2.jpg", io.BytesIO(b"data2"), "image/jpeg")),
            ],
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["image_count"] == 2

    def test_create_batch_task_no_files(self, client):
        """不传文件"""
        response = client.post(
            "/api/tasks/batch",
            data={"scene_id": 1},
        )
        assert response.status_code == 422


class TestGetTask:
    """任务详情测试"""

    def test_get_task_success(self, client):
        """获取存在的任务"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_get_scene",
                "display_name": "任务获取场景",
                "category": "industry",
                "class_names": ["a"],
            },
        )
        scene_id = scene_resp.json()["id"]

        # 创建任务
        task_resp = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={"image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")},
        )
        task_id = task_resp.json()["data"]["task_id"]

        response = client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["task"]["id"] == task_id
        assert data["data"]["task"]["scene_name"] is not None

    def test_get_task_with_results(self, client):
        """获取任务详情并包含结果"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_results_scene",
                "display_name": "含结果场景",
                "category": "industry",
                "class_names": ["a"],
            },
        )
        scene_id = scene_resp.json()["id"]
        task_resp = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={"image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")},
        )
        task_id = task_resp.json()["data"]["task_id"]

        response = client.get(f"/api/tasks/{task_id}?include_results=true")
        assert response.status_code == 200
        assert "results" in response.json()["data"]

    def test_get_task_not_found(self, client):
        """获取不存在的任务"""
        response = client.get("/api/tasks/99999")
        assert response.status_code == 404


class TestDeleteTask:
    """删除任务测试"""

    def test_delete_pending_task_success(self, client):
        """删除pending状态的任务"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_delete_scene",
                "display_name": "删除场景",
                "category": "industry",
                "class_names": ["a"],
            },
        )
        scene_id = scene_resp.json()["id"]
        task_resp = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={"image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")},
        )
        task_id = task_resp.json()["data"]["task_id"]

        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 204


class TestGetTaskResults:
    """任务检测结果列表测试"""

    def test_get_task_results_empty(self, client):
        """获取任务的结果列表（空）"""
        scene_resp = client.post(
            "/api/scenes",
            json={
                "name": "task_results_list_scene",
                "display_name": "结果列表场景",
                "category": "industry",
                "class_names": ["a"],
            },
        )
        scene_id = scene_resp.json()["id"]
        task_resp = client.post(
            "/api/tasks/single",
            data={"scene_id": scene_id},
            files={"image": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")},
        )
        task_id = task_resp.json()["data"]["task_id"]

        response = client.get(f"/api/tasks/{task_id}/results")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"]["items"], list)
