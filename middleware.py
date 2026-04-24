from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        try:
            response = await call_next(request)
            logger.info(f"{request.method} {request.url.path} - {response.status_code} ({time.time()-start:.2f}s)")
            return response
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            raise


def setup_middleware(app):
    app.add_middleware(RequestLoggingMiddleware)