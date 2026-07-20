"""
认证接⼝测试
测试⽬标：
  - ⽤户注册：正常注册、重复⽤户名、参数验证
  - ⽤户登录：正常登录、错误密码、不存在的⽤户
  - 获取当前⽤户：有 Token、⽆ Token、⽆效 Token
测试策略：
  - 每个测试⽤例独⽴，不依赖其他测试的执⾏顺序
  - 使⽤唯⼀的⽤户名避免测试间冲突
"""


import pytest
class TestRegister:
    """⽤户注册测试"""
    def test_register_success(self, client):
        """正常注册"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "test_register_user",
                "email": "test_register@example.com",
                "password": "123456",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "test_register_user"
        assert data["email"] == "test_register@example.com"
        # 确保不返回密码字段
        assert "hashed_password" not in data
        assert "password" not in data
    def test_register_duplicate_username(self, client):
        """重复⽤户名注册"""
        # 先注册⼀个⽤户
        client.post(
            "/api/auth/register",
            json={
                "username": "dup_user",
                "email": "dup1@example.com",
                "password": "123456",
            },
        )
        # ⽤相同⽤户名再注册
        response = client.post(
            "/api/auth/register",
            json={
                "username": "dup_user",
                "email": "dup2@example.com",
                "password": "123456",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data[phone] == 13900139000
    def test_register_short_username(self, client):
        """⽤户名过短（少于 3 字符）"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "ab",
                "email": "short@example.com",
                "password": "123456",
            },
        )
        assert response.status_code == 422
    def test_register_short_password(self, client):
        """密码过短（少于 6 位）"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "short_pwd_user",
                "email": "shortpwd@example.com",
                "password": "123",
            },
        )
        assert response.status_code == 422
    def test_register_missing_fields(self, client):
        """缺少必填字段"""
        response = client.post(
            "/api/auth/register",
            json={"username": "no_email_user"},
        )
        assert response.status_code == 422
class TestLogin:
    """⽤户登录测试"""
    def test_login_success(self, client):
        """正常登录"""
        # 先注册
        client.post(
            "/api/auth/register",
            json={
                "username": "login_user",
                "email": "login@example.com",
                "password": "123456",
            },
        )
        # 再登录
        response = client.post(
            "/api/auth/login",
            json={
                "username": "login_user",
                "password": "123456",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "login_user"
    def test_login_wrong_password(self, client):
        """密码错误"""
        # 先注册
        client.post(
            "/api/auth/register",
            json={
                "username": "wrong_pwd_user",
                "email": "wrongpwd@example.com",
                "password": "123456",
            },
        )
        # ⽤错误密码登录
        response = client.post(
            "/api/auth/login",
            json={
                "username": "wrong_pwd_user",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
    def test_login_nonexistent_user(self, client):
        """不存在的⽤户"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "no_such_user_12345",
                "password": "123456",
            },
        )
        assert response.status_code == 401
class TestGetCurrentUser:
    """获取当前⽤户测试"""
    def test_get_me_with_valid_token(self, client):
        """使⽤有效 Token 获取⽤户信息"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "me_user",
                "email": "me@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "me_user",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]
        # 使⽤ Token 获取⽤户信息
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "me_user"
        assert data["email"] == "me@example.com"
    def test_get_me_without_token(self, client):
        """不带 Token 访问受保护接⼝"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
    def test_get_me_with_invalid_token(self, client):
        """使⽤⽆效 Token"""
        response = client.get("/api/auth/me",headers={"Authorization": "Bearer invalid_token_here"},  )
        assert response.status_code == 401

class TestUpdateProfile:
    """更新用户资料测试"""

    def _register_and_login(self, client, username="profile_user", email="profile@example.com"):
        client.post(
            "/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": "123456",
            },
        )
        return login_response.json()["access_token"]

    def test_update_profile_success(self, client):
        token = self._register_and_login(client, "upd_profile_user", "upd_profile@example.com")
        response = client.patch(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "profile_new@example.com",
                "phone": "13800138000",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile_new@example.com"
        assert data["phone"] == "13800138000"

    def test_update_profile_duplicate_username(self, client):
        client.post(
            "/api/auth/register",
            json={
                "email": "other_dup@example.com",
                "password": "123456",
            },
        )
        token = self._register_and_login(client, "dup_profile_user", "dup_profile@example.com")
        response = client.patch(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"username": "other_user"},
        )
        assert response.status_code == 400


class TestUploadAvatar:
    """上传头像测试"""

    def test_upload_avatar_success(self, client, monkeypatch):
        client.post(
            "/api/auth/register",
            json={
                "username": "avatar_user",
                "email": "avatar@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "avatar_user",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        def fake_upload_bytes(object_name, data, content_type="image/jpeg"):
            assert object_name.startswith("avatars/")
            assert content_type == "image/png"
            return f"http://minio/{object_name}"

        monkeypatch.setattr(
            "app.services.user_service.minio_client.upload_bytes",
            fake_upload_bytes,
        )
        monkeypatch.setattr(
            "app.services.user_service.minio_client.build_public_url",
            lambda object_name: f"/api/storage/{object_name}",
        )

        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        response = client.post(
            "/api/auth/me/avatar",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("avatar.png", png_bytes, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["avatar"].startswith("/api/storage/avatars/")


class TestChangePassword:
    """修改密码测试"""

    def test_change_password_success(self, client):
        client.post(
            "/api/auth/register",
            json={
                "username": "pwd_user",
                "email": "pwd@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "pwd_user",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "123456",
                "new_password": "654321",
            },
        )
        assert response.status_code == 204

        login_old = client.post(
            "/api/auth/login",
            json={
                "username": "pwd_user",
                "password": "123456",
            },
        )
        assert login_old.status_code == 401

        login_new = client.post(
            "/api/auth/login",
            json={
                "username": "pwd_user",
                "password": "654321",
            },
        )
        assert login_new.status_code == 200

    def test_change_password_wrong_old_password(self, client):
        client.post(
            "/api/auth/register",
            json={
                "username": "pwd_wrong_user",
                "email": "pwdwrong@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "pwd_wrong_user",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "wrong-password",
                "new_password": "654321",
            },
        )
        assert response.status_code == 400
