import os
from typing import Optional
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine as sync_engine
from sqlalchemy import text
from sqlalchemy.pool import AsyncAdaptedQueuePool
from gateway.config import get_settings

Base = declarative_base()


# 获取 CPU 核心数，用于动态调整连接池
def _get_optimal_pool_size() -> int:
    try:
        import multiprocessing

        return multiprocessing.cpu_count() * 2 + 1
    except Exception:
        return 20


# Lazily-initialized engine/session objects. They are created in the
# running event loop to avoid asyncpg futures being bound to a different loop.
async_engine: Optional[object] = None
AsyncSessionLocal: Optional[sessionmaker] = None
sync_engine_inst = None
SyncSessionLocal = None


def _ensure_engine():
    global async_engine, AsyncSessionLocal, sync_engine_inst, SyncSessionLocal
    if AsyncSessionLocal is not None:
        return
    settings = get_settings()
    DATABASE_URL = settings.database_url

    # 优化连接池配置
    pool_size = int(os.getenv("DB_POOL_SIZE", _get_optimal_pool_size()))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", pool_size))

    async_engine = create_async_engine(
        DATABASE_URL,
        poolclass=AsyncAdaptedQueuePool,
        pool_pre_ping=True,
        pool_recycle=1800,  # 30分钟回收连接
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=30,
        future=True,
        echo=False,
        connect_args={
            "command_timeout": 60,
            "statement_cache_size": 100,
        },
    )

    AsyncSessionLocal = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    sync_url = DATABASE_URL.replace("+asyncpg", "")
    sync_pool_size = int(os.getenv("DB_SYNC_POOL_SIZE", 5))
    sync_engine_inst = sync_engine(
        sync_url,
        pool_pre_ping=True,
        pool_size=sync_pool_size,
        max_overflow=10,
    )
    SyncSessionLocal = sessionmaker(bind=sync_engine_inst, expire_on_commit=False)


async def get_db_session():
    """获取数据库会话的依赖注入函数（懒创建 engine/session）"""
    _ensure_engine()
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session():
    _ensure_engine()
    return SyncSessionLocal()


async def init_database():
    _ensure_engine()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_admin()


async def _ensure_admin():
    from .tables import User, APIKey

    _ensure_engine()
    async with AsyncSessionLocal() as s:
        admin = await s.get(User, "admin001")
        if admin is None:
            # 如果提供了 ADMIN_PASSWORD，则为 admin 设置密码哈希
            try:
                from gateway.config import get_settings

                settings = get_settings()
                admin_password = getattr(settings, "admin_password", None)
            except Exception:
                admin_password = None

            password_hash = None
            if admin_password:
                salt = bcrypt.gensalt()
                password_hash = bcrypt.hashpw(
                    admin_password.encode("utf-8"), salt
                ).decode("utf-8")

            s.add(
                User(
                    id="admin001",
                    username="admin",
                    email="admin@litellm-gateway.com",
                    role="admin",
                    password_hash=password_hash,
                    budget_limit=10_000,
                    rpm_limit=1000,
                    tpm_limit=1_000_000,
                )
            )
            s.add(
                APIKey(
                    id="admin-key-001",
                    api_key=get_settings().master_key,
                    user_id="admin001",
                    description="Master admin key",
                )
            )
            await s.commit()
