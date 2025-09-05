# app/exceptions.py - 异常处理
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI):
    """设置全局异常处理器"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP异常处理"""
        trace_id = getattr(request.state, 'trace_id', 'unknown')

        logger.warning(
            f"HTTP Exception: {exc.status_code} - {exc.detail} "
            f"- Trace: {trace_id}"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "code": exc.status_code,
                "message": exc.detail,
                "data": None,
                "timestamp": request.state.trace_id if hasattr(request.state, 'trace_id') else None,
                "trace_id": trace_id
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """请求验证异常处理"""
        trace_id = getattr(request.state, 'trace_id', 'unknown')

        logger.warning(
            f"Validation Error: {exc.errors()} "
            f"- Trace: {trace_id}"
        )

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "code": 422,
                "message": "请求参数验证失败",
                "data": {"errors": exc.errors()},
                "trace_id": trace_id
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理"""
        trace_id = getattr(request.state, 'trace_id', 'unknown')

        logger.error(
            f"Unhandled Exception: {str(exc)} "
            f"- Trace: {trace_id}",
            exc_info=True
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "code": 500,
                "message": "服务器内部错误",
                "data": None,
                "trace_id": trace_id
            }
        )
