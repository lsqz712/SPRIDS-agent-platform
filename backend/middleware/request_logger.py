"""
API 请求⽇志中间件
职责：
  - 
  - 
  - 
  - 
记录每个 API 请求的⽅法、路径、客户端 IP
记录请求耗时（毫秒）
记录响应状态码
⾃动跳过健康检查等⾼频接⼝（避免⽇志噪声）
注册⽅式（在 main.py 中）：
  from app.middleware.request_logger import RequestLogMiddleware
  app.add_middleware(RequestLogMiddleware)
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logger import get_logger
logger = get_logger("request")
# 不记录⽇志的路径前缀（⾼频或⽆意义请求）
SKIP_PATHS = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/api/health",     
    # 健康检查频率⾼，不记录
]
class RequestLogMiddleware(BaseHTTPMiddleware):
    """API 请求⽇志中间件"""
    async def dispatch(self, request: Request, call_next):
        """
        拦截每个请求，记录⽇志
        Args:
            request: 当前 HTTP 请求
            call_next: 调⽤链中的下⼀个处理器
        """
        # 检查是否需要跳过
        path = request.url.path
        if any(path.startswith(skip) for skip in SKIP_PATHS):
            return await call_next(request)
        # 记录请求开始
        method = request.method
        client_ip = request.client.host if request.client else "unknown"
        # 获取请求体⼤⼩（如果有）
        content_length = request.headers.get("content-length", "0")
        logger.info(
            "→ %s %s | ip=%s | size=%s",
            method, path, client_ip, content_length,
        )
        # 记录开始时间
        start_time = time.time()
        # 调⽤下⼀个处理器（执⾏业务逻辑）
        response = await call_next(request)
        # 计算耗时
        duration_ms = (time.time() - start_time) * 1000
        # 记录请求结束
        status_code = response.status_code
        # 根据状态码选择⽇志级别
        if status_code >= 500:
            logger.error(
                "← %s %s | status=%d | %.1fms",
                method, path, status_code, duration_ms,
            )
        elif status_code >= 400:
            logger.warning(
                "← %s %s | status=%d | %.1fms",
                method, path, status_code, duration_ms,
            )
        else:
            logger.info(
                "← %s %s | status=%d | %.1fms",
                method, path, status_code, duration_ms,
            )
        return response