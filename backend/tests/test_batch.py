"""
PCB批次接口测试
测试目标：
  - 批次列表：分页、筛选
  - 创建批次：正常创建、批次号唯一性、参数验证
  - 批次详情（含良品率统计）
  - 编辑/删除批次
"""
import pytest


class TestListBatches:
    """批次列表测试"""

    def test_list_batches_pagination(self, client, auth_headers):
        """批次列表分页"""
        response = client.get("/api/batches?page=1&page_size=10", headers = auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10

    def test_list_batches_filter_by_status(self, client, auth_headers):
        """按状态筛选"""
        response = client.get("/api/batches?status=pending", headers = auth_headers)
        assert response.status_code == 200


class TestCreateBatch:
    """创建批次测试"""

    def test_create_success(self, client, auth_headers):
        """正常创建批次"""
        response = client.post(
            "/api/batches",
            headers=auth_headers,
            json={
                "batch_no": "BATCH-20250701-001",
                "pcb_type": "PCB-V2.1",
                "production_line": "LINE-A01",
                "total_count": 1000,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 201
        assert data["data"]["batch_no"] == "BATCH-20250701-001"
        assert data["data"]["status"] == "pending"

    def test_create_duplicate_batch_no(self, client, auth_headers):
        """重复批次号创建失败"""
        client.post(
            "/api/batches",
            headers=auth_headers,
            json={
                "batch_no": "BATCH-DUP-001",
                "pcb_type": "PCB-V1",
                "production_line": "LINE-B01",
                "total_count": 500,
            },
        )
        response = client.post(
            "/api/batches",
            headers=auth_headers,
            json={
                "batch_no": "BATCH-DUP-001",
                "pcb_type": "PCB-V1",
                "production_line": "LINE-B01",
                "total_count": 500,
            },
        )
        assert response.status_code == 400

    def test_create_without_auth(self, client):
        """未认证创建批次"""
        response = client.post(
            "/api/batches",
            json={
                "batch_no": "BATCH-NO-AUTH",
                "pcb_type": "PCB-V1",
                "production_line": "LINE-C01",
                "total_count": 100,
            },
        )
        assert response.status_code == 401

    def test_create_invalid_total_count(self, client, auth_headers):
        """总数量小于1"""
        response = client.post(
            "/api/batches",
            headers=auth_headers,
            json={
                "batch_no": "BATCH-INVALID-COUNT",
                "pcb_type": "PCB-V1",
                "production_line": "LINE-A01",
                "total_count": 0,
            },
        )
        assert response.status_code == 422


class TestGetBatch:
    """批次详情测试"""

    def test_get_batch_success(self, client, auth_headers):
        """获取存在的批次"""
        # 先创建
        resp = client.post(
            "/api/batches",
            headers=auth_headers,
            json={
                "batch_no": "BATCH-GET-001",
                "pcb_type": "PCB-V3",
                "production_line": "LINE-A02",
                "total_count": 2000,
            },
        )
        batch_id = resp.json()["data"]["id"]

        response = client.get(f"/api/batches/{batch_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["batch_no"] == "BATCH-GET-001"
        assert "pass_rate" in data["data"]

    def test_get_batch_not_found(self, client, auth_headers):
        """获取不存在的批次"""
        response = client.get("/api/batches/99999", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateBatch:
    """更新批次测试"""

    def test_update_success(self, client, auth_headers):
        """正常更新批次"""
        resp = client.post(
            "/api/batches",
            headers=auth_headers,
            json={
                "batch_no": "BATCH-UPDATE-001",
                "pcb_type": "PCB-V1",
                "production_line": "LINE-A01",
                "total_count": 1000,
            },
        )
        batch_id = resp.json()["data"]["id"]

        response = client.put(
            f"/api/batches/{batch_id}",
            headers=auth_headers,
            json={"status": "in_progress", "total_count": 1500},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "in_progress"
        assert data["data"]["total_count"] == 1500

    def test_update_not_found(self, client, auth_headers):
        """更新不存在的批次"""
        response = client.put(
            "/api/batches/99999",
            headers=auth_headers,
            json={"status": "completed"},
        )
        assert response.status_code == 404


class TestDeleteBatch:
    """删除批次测试"""

    def test_delete_success(self, client, auth_headers):
        """正常删除批次"""
        resp = client.post(
            "/api/batches",
            headers=auth_headers,
            json={
                "batch_no": "BATCH-DEL-001",
                "pcb_type": "PCB-V1",
                "production_line": "LINE-A01",
                "total_count": 100,
            },
        )
        batch_id = resp.json()["data"]["id"]

        response = client.delete(f"/api/batches/{batch_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_delete_without_auth(self, client, auth_headers):
        """未认证删除"""
        resp = client.post(
            "/api/batches",
            headers=auth_headers,
            json={
                "batch_no": "BATCH-DEL-NOAUTH",
                "pcb_type": "PCB-V1",
                "production_line": "LINE-A01",
                "total_count": 100,
            },
        )
        batch_id = resp.json()["data"]["id"]

        response = client.delete(f"/api/batches/{batch_id}")
        assert response.status_code == 401


class TestBatchStatistics:
    """批次良品率统计测试"""

    def test_batch_statistics(self, client, auth_headers):
        """获取批次统计"""
        resp = client.post(
            "/api/batches",
            headers=auth_headers,
            json={
                "batch_no": "BATCH-STAT-001",
                "pcb_type": "PCB-V1",
                "production_line": "LINE-A01",
                "total_count": 500,
            },
        )
        batch_id = resp.json()["data"]["id"]

        response = client.get(
            f"/api/batches/{batch_id}/statistics", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["batch_id"] == batch_id
        assert "pass_rate" in data["data"]
        assert "fail_rate" in data["data"]
