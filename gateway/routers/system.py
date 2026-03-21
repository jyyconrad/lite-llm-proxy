import uuid
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import yaml, os
from sqlalchemy import select, func
import asyncio

from gateway.routers.admin import randstr
from ..models import UserRegister, UserLogin
from ..dependencies import (
    hash_password,
    verify_password,
    get_db_session,
    authenticate_user,
    require_admin,
    get_redis,
)
from data import User, APIKey
from config_manager import get_all_models

router = APIRouter()


@router.get("/health")
async def health():
    """基础健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@router.get("/health/detailed")
async def detailed_health():
    """详细健康检查 - 检查各组件状态"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {},
    }

    # 检查数据库
    try:
        from data.db import async_engine

        if async_engine is not None:
            async with async_engine.connect() as conn:
                await conn.execute("SELECT 1")
            health_status["components"]["database"] = {"status": "healthy"}
        else:
            health_status["components"]["database"] = {"status": "not_initialized"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "unhealthy"

    # 检查 Redis
    try:
        r = await get_redis()
        await r.ping()
        health_status["components"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"

    # 检查配置加载
    try:
        models = get_all_models()
        health_status["components"]["config"] = {
            "status": "healthy",
            "models_count": len(models),
        }
    except Exception as e:
        health_status["components"]["config"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"

    # 设置 HTTP 状态码
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


@router.get("/models")
def list_models():
    try:
        models = get_all_models()
        return {"models": models}
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(500, f"fetch models error: {e}")


@router.get("/models/all")
def list_all_models():
    """获取所有模型的详细信息"""
    try:
        from config_manager import get_all_model_configs

        configs = get_all_model_configs()

        models_list = []
        for model_name, config in configs.items():
            endpoints = []
            if hasattr(config, "litellm_params"):
                params = config.litellm_params
                if hasattr(params, "endpoints"):
                    for ep in params.endpoints:
                        endpoints.append(
                            {
                                "model": ep.model,
                                "provider": ep.provider,
                                "base_url": ep.base_url,
                                "weight": ep.weight,
                                "max_tokens": ep.max_tokens,
                                "rpm": ep.rpm,
                                "tpm": ep.tpm,
                            }
                        )
                else:
                    endpoints.append(
                        {
                            "model": params.model,
                            "provider": params.provider,
                            "base_url": params.base_url,
                            "weight": params.weight,
                            "max_tokens": params.max_tokens,
                            "rpm": params.rpm,
                            "tpm": params.tpm,
                        }
                    )

            models_list.append(
                {
                    "model_name": config.model_name,
                    "description": config.description,
                    "support_types": config.support_types,
                    "default_rpm": config.default_rpm,
                    "default_tpm": config.default_tpm,
                    "default_max_tokens": config.default_max_tokens,
                    "endpoints": endpoints,
                }
            )

        return {"models": models_list, "total": len(models_list)}
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(500, f"fetch models error: {e}")


@router.post("/auth/register")
async def register_user(user_data: UserRegister, db=Depends(get_db_session)):
    """用户注册"""
    # 检查用户名和邮箱是否已存在
    stmt = select(User).where(
        (User.username == user_data.username) | (User.email == user_data.email)
    )
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    # 创建新用户
    user_id = str(uuid.uuid4())
    password_hash = hash_password(user_data.password)

    new_user = User(
        id=user_id,
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        role=user_data.role,
    )

    db.add(new_user)
    await db.commit()

    # 为用户自动生成API密钥
    api_key = f"sk-{uuid.uuid4().hex}"
    new_api_key = APIKey(
        id=str(uuid.uuid4()),
        api_key=api_key,
        user_id=user_id,
        description="自动生成的API密钥",
    )
    db.add(new_api_key)
    await db.commit()

    return {
        "message": "用户注册成功",
        "user_id": user_id,
        "api_key": api_key,
        "username": user_data.username,
        "email": user_data.email,
    }


@router.post("/auth/login")
async def login_user(login_data: UserLogin, db=Depends(get_db_session)):
    """用户登录"""
    # 查找用户
    stmt = select(User).where(User.username == login_data.username)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证密码
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 检查用户状态
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户账户已被禁用")

    # 获取用户的API密钥
    key_stmt = select(APIKey).where(
        (APIKey.user_id == user.id) & (APIKey.is_active == True)
    )
    result = await db.execute(key_stmt)
    api_key_row = result.scalars().first()

    if not api_key_row:
        raise HTTPException(status_code=500, detail="用户没有有效的API密钥")

    return {
        "message": "登录成功",
        "api_key": api_key_row.api_key,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


@router.get("/auth/me")
async def get_current_user(user=Depends(authenticate_user), db=Depends(get_db_session)):
    """获取当前用户信息"""
    # 从数据库获取完整的用户信息
    stmt = select(User).where(User.id == user["user_id"])
    result = await db.execute(stmt)
    user_row = result.scalars().first()

    if not user_row:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "id": user_row.id,
        "username": user_row.username,
        "email": user_row.email,
        "role": user_row.role,
        "budget_limit": float(user_row.budget_limit or 0),
        "rpm_limit": int(user_row.rpm_limit or 0),
        "tpm_limit": int(user_row.tpm_limit or 0),
        "is_active": user_row.is_active,
        "created_at": user_row.created_at.isoformat() if user_row.created_at else None,
    }


@router.get("/users")
async def get_users(
    page: int = 1,
    per_page: int = 20,
    admin=Depends(require_admin),
    db=Depends(get_db_session),
):
    """获取所有用户列表（仅管理员），支持分页"""
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 200:
        per_page = 20

    stmt = (
        select(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()

    # total count
    total = (await db.execute(select(func.count(User.id)))).scalar() or 0

    return {
        "page": page,
        "per_page": per_page,
        "total": int(total),
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "budget_limit": float(user.budget_limit or 0),
                "rpm_limit": int(user.rpm_limit or 0),
                "tpm_limit": int(user.tpm_limit or 0),
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            for user in users
        ],
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: dict,
    admin=Depends(require_admin),
    db=Depends(get_db_session),
):
    """更新用户信息（仅管理员）"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新允许修改的字段
    allowed_fields = [
        "username",
        "email",
        "role",
        "budget_limit",
        "rpm_limit",
        "tpm_limit",
        "is_active",
    ]
    for field in allowed_fields:
        if field in user_data:
            setattr(user, field, user_data[field])

    await db.commit()
    return {"message": "用户信息更新成功"}


@router.post("/users/{user_id}/enable")
async def enable_user(
    user_id: str, admin=Depends(require_admin), db=Depends(get_db_session)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_active = True
    await db.commit()
    return {"message": "用户已启用"}


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str, admin=Depends(require_admin), db=Depends(get_db_session)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.is_active = False
    await db.commit()
    return {"message": "用户已停用"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    password_data: dict,
    admin=Depends(require_admin),
    db=Depends(get_db_session),
):
    """重置用户密码（仅管理员）"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    new_password = password_data.get("new_password")
    if not new_password:
        raise HTTPException(status_code=400, detail="新密码不能为空")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少为6位")

    # 生成密码哈希
    password_hash = hash_password(new_password)
    user.password_hash = password_hash

    await db.commit()
    return {"message": "密码重置成功"}


@router.post("/users/{user_id}/api-keys")
async def create_user_api_key(
    user_id: str,
    key_data: dict,
    admin=Depends(require_admin),
    db=Depends(get_db_session),
):
    """为用户创建新的API密钥（仅管理员）"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    description = key_data.get("description", "手动创建的API密钥")
    api_key = f"sk-{uuid.uuid4().hex}"

    new_api_key = APIKey(
        id=str(uuid.uuid4()), api_key=api_key, user_id=user_id, description=description
    )
    db.add(new_api_key)
    await db.commit()

    return {
        "message": "API密钥创建成功",
        "api_key": api_key,
        "description": description,
    }


@router.post("/auth/api-keys")
async def create_own_api_key(
    key_data: dict = {}, user=Depends(authenticate_user), db=Depends(get_db_session)
):
    """当前登录用户为自己创建 API Key"""
    user_id = user["user_id"]
    description = key_data.get("description", "用户自助创建的API密钥")
    api_key = f"sk-{randstr(8)}"

    new_api_key = APIKey(
        id=str(uuid.uuid4()), api_key=api_key, user_id=user_id, description=description
    )
    db.add(new_api_key)
    await db.commit()

    return {
        "message": "API密钥创建成功",
        "api_key": api_key,
        "description": description,
        "id": new_api_key.id,
    }


@router.get("/auth/api-keys")
async def list_own_api_keys(
    user=Depends(authenticate_user), db=Depends(get_db_session)
):
    """列出当前登录用户的 API keys"""
    stmt = (
        select(APIKey)
        .where(APIKey.user_id == user["user_id"])
        .order_by(APIKey.created_at.desc())
    )
    result = await db.execute(stmt)
    keys = result.scalars().all()
    return keys


@router.patch("/auth/api-keys/{key_id}/disable")
async def disable_own_key(
    key_id: str, user=Depends(authenticate_user), db=Depends(get_db_session)
):
    """用户禁用自己的 API Key"""
    key = await db.get(APIKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    if key.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="不能操作非本用户的 API key")
    key.is_active = False
    await db.commit()
    return {"message": "API key disabled successfully"}


@router.patch("/auth/api-keys/{key_id}/enable")
async def enable_own_key(
    key_id: str, user=Depends(authenticate_user), db=Depends(get_db_session)
):
    """用户启用自己的 API Key"""
    key = await db.get(APIKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    if key.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="不能操作非本用户的 API key")
    key.is_active = True
    await db.commit()
    return {"message": "API key enabled successfully"}
