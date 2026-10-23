"""Security headers, a request size cap and a sign in rate limit for every response.

The rate limit counts sign in attempts per client address in a sliding minute,
on top of the per account lockout in ``AuthService``. It is held in memory,
which suits the single process the deployment runs.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

MAX_BODY_BYTES = 64 * 1024
SIGN_INS_PER_MINUTE = 20
DOCS = ("/docs", "/redoc", "/openapi.json")
HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}
POLICY = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
    "form-action 'self'"
)


def _refused(status: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"detail": [{"field": "request", "message": message}]}
    )


def install(app: FastAPI) -> None:
    """Add the security middleware to ``app``."""
    attempts: dict[str, deque[float]] = defaultdict(deque)

    @app.middleware("http")
    async def protect(request: Request, call_next):
        if int(request.headers.get("content-length") or 0) > MAX_BODY_BYTES:
            return _refused(413, "The request is too large.")
        if request.url.path == "/api/auth/sign-in" and request.method == "POST":
            client = request.client.host if request.client else "unknown"
            window, now = attempts[client], time.monotonic()
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= SIGN_INS_PER_MINUTE:
                return _refused(429, "Too many sign in attempts from this address. Wait a minute.")
            window.append(now)
        response = await call_next(request)
        response.headers.update(HEADERS)
        if not request.url.path.startswith(DOCS):
            response.headers["Content-Security-Policy"] = POLICY
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response
