"""
pytest 全局 Fixtures
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    """覆盖 FastAPI 的 get_db 依赖，使用测试数据库"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


from app.entity import db_models  # noqa: E402, F401
from main import app  # noqa: E402

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """创建测试数据库表"""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def client():
    """提供 FastAPI 测试客户端"""
    return TestClient(app)


@pytest.fixture
def db_session():
    """提供独立的数据库会话"""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def auth_headers(client):
    """
    提供已认证的请求头（注册 + 登录后返回 Bearer Token）
    ⽤法：
    def test_xxx(client, auth_headers):
        response = client.get("/api/xxx", headers=auth_headers)
    """
    # 注册测试用户
    client.post(
        "/api/auth/register",
        json={
            "username": "test_auth_user",
            "email": "test_auth@example.com",
            "password": "123456",
        },
    )
    # 登录获取 Token
    login_resp = client.post(
        "/api/auth/login",
        json={
            "username": "test_auth_user",
            "password": "123456",
        },
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
