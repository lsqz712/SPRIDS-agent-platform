from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time

logger = logging.getLogger(__name__)

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"请求异常: {request.method} {request.url} - {str(e)}")
            raise
        process_time = time.time() - start_time
        logger.info(f"{request.method} {request.url} {response.status_code} - {process_time:.2f}s")
        return response