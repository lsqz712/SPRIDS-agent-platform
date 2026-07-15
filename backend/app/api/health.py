from fastapi import APIRouter

router = APIRouter(tags=["健康检查"])


@router.get("/api/health")
async def health_check():
    return {"code": 200, "message": "ok", "data": {"status": "healthy", "app_name": "SPRIDS Agent Platform", "version": "0.1.0"}}


@router.get("/api/health/redis")
async def redis_debug():
    """
    Redis 数据调试接口

    用途：查看 Redis 中存储的所有键值数据
    注意：生产环境建议关闭此接口或添加权限控制
    """
    try:
        from app.storage.redis_client import redis_client

        data = redis_client.get_all_data()
        return {
            "code": 200,
            "message": "ok",
            "data": {
                "use_redis": redis_client.info()["use_redis"],
                "key_count": len(data),
                "data": data,
            },
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"获取 Redis 数据失败: {str(e)}",
            "data": None,
        }


@router.get("/api/health/redis/info")
async def redis_info():
    """
    Redis 客户端状态信息

    用途：查看 Redis 连接状态、键数量等信息
    """
    try:
        from app.storage.redis_client import redis_client

        info = redis_client.info()
        return {
            "code": 200,
            "message": "ok",
            "data": info,
        }
    except Exception as e:
        return {
            "code": 500,
            "message": f"获取 Redis 状态失败: {str(e)}",
            "data": None,
        }