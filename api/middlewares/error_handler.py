from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import traceback
import logging

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            error_details = {
                "path": request.url.path,
                "method": request.method,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            logger.error(f"Unhandled error: {error_details}")

            return JSONResponse(
                status_code=500,
                content={
                    "detail": "An internal server error occurred.",
                    "error": str(e) if not isinstance(e, HTTPException) else e.detail
                }
            )