import logging
import os
import gzip
import shutil
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .local_model_manage import initialize_local_models
from .config import get_settings
from .routers import system, llm, admin
from .dependencies import AuthException

# 为了在与运行时相同的事件循环中初始化数据库
from data import init_database


# 配置日志
def setup_logging():
    settings = get_settings()

    # 创建日志目录
    log_dir = os.path.dirname(settings.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 配置日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # 清除现有的处理器
    root_logger.handlers.clear()

    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 添加文件处理器（按时间和大小轮转）
    # TimedRotatingFileHandler: 按时间轮转（每天午夜）
    # RotatingFileHandler: 按大小轮转（当文件达到 maxBytes 时）

    # 使用 TimedRotatingFileHandler 按天轮转，并处理大小限制
    file_handler = TimedRotatingFileHandler(
        settings.log_file,
        when="midnight",  # 每天午夜轮转
        interval=1,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.suffix = ".%Y-%m-%d.log"  # 设置文件名后缀格式

    # 重写 namer 方法来实现大小限制的文件压缩和命名
    def get_time_based_filename(base_name, suffix, ext=".log"):
        """生成基于时间的文件名"""
        dir_name, file_name = os.path.split(base_name)
        return os.path.join(dir_name, f"{file_name}{suffix}{ext}")

    # 重写 rollover 方法来结合时间和大小的轮转
    original_emit = file_handler.emit

    def emit_with_size_check(record):
        """重写 emit 方法，在每次写入前检查文件大小"""
        if file_handler.baseFilename:
            try:
                # 检查文件大小是否超过限制
                if os.path.exists(file_handler.baseFilename):
                    file_size = os.path.getsize(file_handler.baseFilename)
                    if file_size >= settings.log_max_bytes:
                        # 立即执行轮转（不等待时间）
                        file_handler.doRollover()
            except Exception:
                pass  # 忽略大小检查时的异常
        original_emit(record)

    file_handler.emit = emit_with_size_check

    # 重写 doRollover 方法，添加 gzip 压缩
    original_doRollover = file_handler.doRollover

    def doRollover_with_compress():
        """执行轮转并压缩旧的日志文件"""
        original_doRollover()

        # 查找所有未压缩的备份文件（.log 结尾）并压缩
        base_name = file_handler.baseFilename
        if os.path.exists(base_name):
            dir_name = os.path.dirname(base_name)
            if not dir_name:
                dir_name = "."
            base_file = os.path.basename(base_name)

            # 查找所有 .log 文件（排除当前正在写入的文件）
            for filename in os.listdir(dir_name):
                if filename.startswith(base_file) and filename.endswith(".log"):
                    full_path = os.path.join(dir_name, filename)
                    # 跳过当前正在写入的文件
                    if full_path != base_name:
                        try:
                            # 压缩文件
                            with open(full_path, "rb") as f_in:
                                with gzip.open(full_path + ".gz", "wb") as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            # 删除原始文件
                            os.remove(full_path)
                        except Exception:
                            pass  # 忽略压缩时的异常

    file_handler.doRollover = doRollover_with_compress

    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger


def create_app() -> FastAPI:
    load_dotenv()
    # 初始化日志
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting LiteLLM API Gateway")

    app = FastAPI(title="LiteLLM API Gateway", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加全局异常处理器
    @app.exception_handler(AuthException)
    async def auth_exception_handler(request: Request, exc: AuthException):
        logger.warning(
            f"Authentication exception: {exc.detail} (status_code: {exc.status_code})"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"type": "AuthException", "message": exc.detail}},
        )

    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP exception: {exc.detail} (status_code: {exc.status_code})")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"type": "HTTPException", "message": exc.detail}},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {"type": "InternalServerError", "message": "服务器内部错误"}
            },
        )

    # 注册API路由（必须在静态文件之前注册）
    app.include_router(system.router, tags=["system"])
    app.include_router(llm.router, prefix="/v1", tags=["openai"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])

    # 注册 metrics 路由
    from .metrics import router as metrics_router

    app.include_router(metrics_router, tags=["metrics"])

    # 2. 静态资源（js / css / assets）
    app.mount("/app", StaticFiles(directory="dist", html=True), name="static")

    # 3. SPA fallback（最后）
    @app.get("/")
    async def index():
        return {"message": "API running"}

    @app.on_event("startup")
    async def _startup_db():
        try:
            await init_database()
            logger.info("Database initialized on startup")

            initialize_local_models()

            # 执行配置同步
            from gateway.services.config_sync_service import get_config_sync_service
            from data.db import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                sync_service = get_config_sync_service()
                result = await sync_service.sync_on_startup(session)
                logger.info(f"配置同步完成：{result}")
        except Exception as e:
            logger.exception(f"启动失败：{e}")
            raise

    return app
