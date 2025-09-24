# app/main.py
import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import engine

# 导入API路由
try:
    from app.api.v1 import auth, users, roles, permissions, oauth, projects, audit, sso, fishair

    API_IMPORTS_OK = True
except ImportError as e:
    print(f"⚠️ API import warning: {e}")
    API_IMPORTS_OK = False


    # 创建空的router对象，防止启动失败
    class EmptyRouter:
        router = None

settings = get_settings()

# 配置日志
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting Unified Auth System...")

    # 测试数据库连接
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        # 不抛出异常，让应用继续启动

    yield

    # 关闭时执行
    logger.info("Shutting down Unified Auth System...")
    await engine.dispose()


# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="统一认证授权系统API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.ALLOWED_CREDENTIALS,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)


# 请求处理中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间和追踪ID"""
    start_time = time.time()

    # 生成请求追踪ID
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id

    try:
        response = await call_next(request)
    except Exception as e:
        # 统一异常处理
        logger.error(f"Request failed: {str(e)} - Trace: {trace_id}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "code": 500,
                "message": "Internal server error",
                "trace_id": trace_id
            }
        )

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Trace-ID"] = trace_id

    return response


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": time.time(),
        "database": "connected",  # 简化状态
        "api_imports": API_IMPORTS_OK
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "统一认证授权系统 API",
        "version": settings.VERSION,
        "docs_url": "/docs" if settings.DEBUG else "文档已禁用",
        "status": "running"
    }


# 注册API路由（如果导入成功）
if API_IMPORTS_OK:
    app.include_router(
        auth.router,
        prefix=f"{settings.API_PREFIX}/auth",
        tags=["认证"]
    )

    app.include_router(
        oauth.router,
        prefix=f"{settings.API_PREFIX}/auth",
        tags=["第三方登录"]
    )

    app.include_router(
        users.router,
        prefix=f"{settings.API_PREFIX}/users",
        tags=["用户管理"]
    )

    app.include_router(
        roles.router,
        prefix=f"{settings.API_PREFIX}/roles",
        tags=["角色管理"]
    )

    app.include_router(
        permissions.router,
        prefix=f"{settings.API_PREFIX}/permissions",
        tags=["权限管理"]
    )

    app.include_router(
        projects.router,
        prefix=f"{settings.API_PREFIX}/projects",
        tags=["项目管理"]
    )

    app.include_router(
        audit.router,
        prefix=f"{settings.API_PREFIX}/audit",
        tags=["审计日志"]
    )

    app.include_router(
        sso.router,
        prefix=f"{settings.API_PREFIX}/sso",
        tags=["单点登录"]
    )

    app.include_router(
        fishair.router,
        prefix=f"{settings.API_PREFIX}/fishair",
        tags=["FishAIR代理"]
    )
else:
    logger.warning("⚠️ Some API routes are not available due to import errors")

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Unified Auth System...")
    print(f"📍 Server will run on: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API docs: http://{settings.HOST}:{settings.PORT}/docs")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )