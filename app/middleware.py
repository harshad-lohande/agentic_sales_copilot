# app/middleware.py

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from .logging_config import set_correlation_id, logger


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Correlation-ID")
        cid = incoming or str(uuid.uuid4())
        set_correlation_id(cid)
        logger.info({"message": "Inbound request received", "path": request.url.path})
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
