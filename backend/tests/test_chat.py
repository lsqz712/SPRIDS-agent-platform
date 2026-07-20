"""Chat API tests"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@pytest.fixture
def auth_token(client):
    """注册用户并返回有效的 JWT token"""
    client.post(
        "/api/auth/register",
        json={
            "username": "chat_test_user",
            "email": "chat_test@example.com",
            "password": "123456",
        },
    )
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "chat_test_user", "password": "123456"},
    )
    return login_resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


def test_chat_stream_requires_auth():
    response = client.post("/api/chat/stream", json={"message": "你好"})
    assert response.status_code == 401


@patch("app.api.chat.detection_agent.chat_stream")
def test_chat_stream_success(mock_chat_stream, auth_headers):
    async def fake_stream(*_args, **_kwargs):
        yield {"type": "text", "content": "你好"}
        yield {"type": "text", "content": "，旅人。"}

    mock_chat_stream.side_effect = fake_stream

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "你好", "history": []},
        headers=auth_headers,
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
        assert "你好" in body
        assert "[DONE]" in body
