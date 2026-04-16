"""Global error handler middleware"""
import logging
import traceback
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(
                f"[ERROR] {request.method} {request.url.path} — {type(exc).__name__}: {exc}\n"
                f"{traceback.format_exc()}"
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "เกิดข้อผิดพลาดภายในระบบ",
                    "detail": str(exc) if request.app.extra.get("debug") else None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": str(request.url.path),
                },
            )
