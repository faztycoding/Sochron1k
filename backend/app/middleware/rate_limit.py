"""Simple in-memory rate limiter middleware"""
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60, burst: int = 10):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst = burst
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, ip: str) -> Tuple[bool, int]:
        now = time.time()
        window = now - 60

        self.requests[ip] = [t for t in self.requests[ip] if t > window]
        count = len(self.requests[ip])

        if count >= self.rpm:
            retry_after = int(self.requests[ip][0] + 60 - now) + 1
            return True, retry_after

        self.requests[ip].append(now)
        return False, 0

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)

        ip = self._get_client_ip(request)
        limited, retry_after = self._is_rate_limited(ip)

        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"ส่ง request เกินกำหนด ({self.rpm}/นาที)",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        remaining = self.rpm - len(self.requests[ip])
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response
