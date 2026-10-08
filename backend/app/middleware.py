"""Cross-cutting HTTP concerns: request IDs for log correlation, and standard security headers."""

import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach an ID to every request, echo it as X-Request-ID, and make it available to log records.

    An incoming X-Request-ID is honoured only if it is a UUID, so clients can't inject log noise.
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        try:
            request_id = str(uuid.UUID(incoming))
        except ValueError:
            request_id = str(uuid.uuid4())

        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response


class RequestIdFilter(logging.Filter):
    """Adds `request_id` to every log record so the log format can include it."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True
