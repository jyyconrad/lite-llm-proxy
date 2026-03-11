import secrets
import string
import uuid, asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_, Numeric
from typing import List, Optional
from ..models import UserCreate, UserResponse, APIKeyCreate, APIKeyResponse
from ..dependencies import (
    authenticate_user,
    get_db_session,
    incr_rate_limit,
    require_admin,
)
from data import User, APIKey, UsageStat, CompletionLog

router = APIRouter()
ALPHABET = string.ascii_letters + string.digits  # 62 个字符


def randstr(n: int = 16) -> str:
    """生成 n 位、URL 安全、大小写字母+数字的随机串"""
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


# ---- 用户管理 ----
@router.post("/users")
async def create_user(
    uc: UserCreate, admin=Depends(require_admin), db=Depends(get_db_session)
):
    """管理员创建用户并自动生成 API Key，返回用户信息与明文 api_key（仅管理员可见）。"""
    uid = str(uuid.uuid4())
    new_user = User(id=uid, **uc.model_dump())
    db.add(new_user)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="username or email exists")

    # 生成 API Key 并保存
    try:
        api_key_val = f"sk-{randstr(8)}"
        new_key = APIKey(
            id=str(uuid.uuid4()),
            api_key=api_key_val,
            user_id=uid,
            description="自动生成的API密钥（管理员创建）",
        )
        db.add(new_key)
        await db.commit()
    except Exception:
        await db.rollback()
        # 用户已创建，但密钥创建失败——返回用户信息并提示密钥创建失败
        user_obj = await db.get(User, uid)
        return {
            "user": {
                "id": user_obj.id,
                "username": user_obj.username,
                "email": user_obj.email,
                "role": user_obj.role,
                "rpm_limit": user_obj.rpm_limit,
                "tpm_limit": user_obj.tpm_limit,
                "is_active": user_obj.is_active,
                "created_at": user_obj.created_at.isoformat()
                if user_obj.created_at
                else None,
            },
            "api_key": None,
            "warning": "用户已创建，但生成 API key 失败",
        }

    # 成功：返回用户简要信息和明文 api_key（仅管理员可见）
    user_obj = await db.get(User, uid)
    return {
        "id": user_obj.id,
        "username": user_obj.username,
        "email": user_obj.email,
        "role": user_obj.role,
        "rpm_limit": user_obj.rpm_limit,
        "tpm_limit": user_obj.tpm_limit,
        "is_active": user_obj.is_active,
        "created_at": user_obj.created_at.isoformat() if user_obj.created_at else None,
        "api_key": api_key_val,
    }


@router.get("/users", response_model=List[UserResponse])
async def list_users(admin=Depends(require_admin), db=Depends(get_db_session)):
    """获取所有用户列表"""
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


# ---- 密钥管理 ----
@router.post("/api-keys")
async def create_key(
    ak: APIKeyCreate, admin=Depends(require_admin), db=Depends(get_db_session)
):
    key_val = f"sk-{randstr(8)}"
    db.add(
        APIKey(
            id=str(uuid.uuid4()),
            api_key=key_val,
            user_id=ak.user_id,
            description=ak.description,
        )
    )
    await db.commit()
    return await db.get(APIKey, key_val)


@router.get("/api-keys")
async def list_keys(admin=Depends(require_admin), db=Depends(get_db_session)):
    """获取所有API密钥列表"""
    stmt = select(APIKey).order_by(APIKey.created_at.desc())
    result = await db.execute(stmt)
    keys = result.scalars().all()
    return keys


@router.get("/api-keys/{key_id}")
async def get_key(
    key_id: str, admin=Depends(require_admin), db=Depends(get_db_session)
):
    """获取特定API密钥信息"""
    key = await db.get(APIKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return key


@router.patch("/api-keys/{key_id}/disable")
async def disable_key(
    key_id: str, admin=Depends(require_admin), db=Depends(get_db_session)
):
    """禁用API密钥"""
    key = await db.get(APIKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    await db.commit()
    return {"message": "API key disabled successfully"}


@router.patch("/api-keys/{key_id}/enable")
async def enable_key(
    key_id: str, admin=Depends(require_admin), db=Depends(get_db_session)
):
    """启用API密钥"""
    key = await db.get(APIKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = True
    await db.commit()
    return {"message": "API key enabled successfully"}


@router.delete("/api-keys/{key_id}")
async def delete_key(
    key_id: str, admin=Depends(require_admin), db=Depends(get_db_session)
):
    """删除API密钥"""
    key = await db.get(APIKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(key)
    await db.commit()
    return {"message": "API key deleted successfully"}


@router.get("/users/{user_id}/key")
async def get_user_key(
    user_id: str, admin=Depends(require_admin), db=Depends(get_db_session)
):
    """管理员专用：获取指定用户的最新可用 API 密钥值。"""
    # 查询该用户最新创建且仍然存在的 API Key（按创建时间降序）
    stmt = (
        select(APIKey)
        .where(APIKey.user_id == user_id)
        .order_by(APIKey.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    key = result.scalars().first()
    if not key:
        raise HTTPException(status_code=404, detail="API key for user not found")

    # 仅在管理员权限下返回密钥值（注意：这是敏感信息，请谨慎使用）
    return {
        "id": key.id,
        "api_key": key.api_key,
        "description": key.description,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "is_active": bool(key.is_active),
    }


# ---- 个人用量 ----
@router.get("/stats/usage")
async def self_usage(u=Depends(authenticate_user), db=Depends(get_db_session)):
    # 构建 where 条件（基于 CompletionLog）
    where_clauses = []
    # if model:
    #     where_clauses.append(CompletionLog.model_name == model)
    if u.get("role") != "admin":
        where_clauses.append(UsageStat.user_id == u["user_id"])
    stmt = select(
        func.sum(UsageStat.request_count).label("calls"),
        func.sum(UsageStat.total_tokens).label("tokens"),
        func.sum(UsageStat.total_cost).label("cost"),
    ).where(**where_clauses)

    result = await db.execute(stmt)
    row = result.first()
    return {
        "user_id": u["user_id"],
        "total_calls": int(row.calls or 0),
        "total_tokens": int(row.tokens or 0),
        "total_cost": (row.cost or 0),
        "budget_used": (row.cost or 0),
        "budget_limit": (u["budget_limit"]),
        "rate_limit": u["rpm_limit"],
    }


# ---- 统计接口 ----
@router.get("/stats/overview")
async def stats_overview(u=Depends(authenticate_user), db=Depends(get_db_session)):
    """系统概览统计"""
    # 构建 where 条件（基于 CompletionLog）
    where_clauses = []
    # if model:
    #     where_clauses.append(CompletionLog.model_name == model)
    if u.get("role") != "admin":
        where_clauses.append(UsageStat.user_id == u["user_id"])
    # 总调用次数
    total_calls = (
        await db.execute(
            select(func.sum(UsageStat.request_count)).where(*where_clauses)
        )
    ).scalar() or 0

    # 总 tokens
    total_tokens = (
        await db.execute(select(func.sum(UsageStat.total_tokens)).where(*where_clauses))
    ).scalar() or 0

    # 总成本 —— 不再 cast，直接 sum(NUMERIC)
    total_cost = (
        await db.execute(select(func.sum(UsageStat.total_cost)).where(*where_clauses))
    ).scalar() or 0

    # 活跃用户数（最近 24h）
    active_users = (
        await db.execute(
            select(func.count(func.distinct(UsageStat.user_id))).where(
                UsageStat.last_used >= datetime.now() - timedelta(hours=24)
            )
        )
    ).scalar() or 0

    # 总用户数
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # 其余字段保持默认值即可
    return {
        "total_calls": int(total_calls),
        "total_tokens": int(total_tokens),
        "active_users": int(active_users),
        "total_users": int(total_users),
        "total_cost": total_cost,
        "cost_trend": "",
        "success_rate": 100,
        "avg_response_time": "/",
    }


@router.get("/stats/model-usage")
async def model_usage_stats(u=Depends(authenticate_user), db=Depends(get_db_session)):
    """模型使用统计"""
    # 构建 where 条件（基于 CompletionLog）
    where_clauses = []
    # if model:
    #     where_clauses.append(CompletionLog.model_name == model)
    if u.get("role") != "admin":
        where_clauses.append(UsageStat.user_id == u["user_id"])
    stmt = (
        select(
            UsageStat.model_name,
            func.sum(UsageStat.request_count).label("call_count"),
            func.sum(UsageStat.total_tokens).label("total_tokens"),
            func.sum(UsageStat.total_cost).label("total_cost"),
        )
        .where(*where_clauses)
        .group_by(UsageStat.model_name)
    )

    results = await db.execute(stmt)
    stats = []

    for row in results:
        stats.append(
            {
                "model_name": row.model_name,
                "call_count": row.call_count or 0,
                "total_tokens": row.total_tokens or 0,
                "total_cost": (row.total_cost or 0) if row.total_cost else 0.0,
                "avg_response_time": 1240,  # 需要响应时间数据，暂时使用默认值
                "success_rate": 0.98,  # 需要错误数据，暂时使用默认值
                "status": "active",  # 需要模型状态数据，暂时使用默认值
            }
        )

    return stats


@router.get("/stats/recent-activity")
async def recent_activity(
    limit: int = 10, u=Depends(authenticate_user), db=Depends(get_db_session)
):
    """最近活动记录"""
    from datetime import datetime

    # 构建 where 条件（基于 CompletionLog）
    where_clauses = []
    # if model:
    #     where_clauses.append(CompletionLog.model_name == model)
    if u.get("role") != "admin":
        where_clauses.append(UsageStat.user_id == u["user_id"])
    # 实际应该有一个单独的请求记录表
    stmt = (
        select(
            UsageStat.user_id,
            UsageStat.model_name,
            func.sum(UsageStat.request_count).label("request_count"),
            func.sum(UsageStat.total_tokens).label("total_tokens"),
            func.sum(UsageStat.total_cost).label("total_cost"),
            func.max(UsageStat.last_used).label("last_used"),
        )
        .where(*where_clauses)
        .group_by(UsageStat.user_id, UsageStat.model_name)
        .order_by(func.max(UsageStat.last_used).desc())
        .limit(limit)
    )

    results = await db.execute(stmt)
    activities = []

    for row in results:
        # 获取用户信息
        user_stmt = select(User.email).where(User.id == row.user_id)
        user_result = await db.execute(user_stmt)
        user_email = user_result.scalar() or "unknown"

        activities.append(
            {
                "id": f"req_{row.user_id}_{row.model_name}",  # 模拟请求ID
                "user_email": user_email,
                "model_name": row.model_name,
                "total_tokens": row.total_tokens or 0,
                "cost": (row.total_cost or 0) if row.total_cost else 0.0,
                "timestamp": row.last_used.isoformat()
                if row.last_used
                else datetime.utcnow().isoformat(),
                "success": True,  # 需要错误数据，暂时设为True
                "response_time": 1250,  # 需要响应时间数据，暂时使用默认值
            }
        )

    return activities


@router.get("/stats/user/{user_id}")
async def user_stats(user_id: str, db=Depends(get_db_session)):
    """用户详细统计"""
    # 用户基本信息
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 用户使用统计
    usage_stmt = select(
        func.sum(UsageStat.request_count).label("total_calls"),
        func.sum(UsageStat.total_tokens).label("total_tokens"),
        func.sum(UsageStat.total_cost).label("total_cost"),
        func.array_agg(func.distinct(UsageStat.model_name)).label("active_models"),
        func.max(UsageStat.last_used).label("last_activity"),
    ).where(UsageStat.user_id == user_id)

    usage_result = await db.execute(usage_stmt)
    usage_row = usage_result.first()

    return {
        "user_id": user_id,
        "email": user.email,
        "total_calls": usage_row.total_calls or 0,
        "total_tokens": usage_row.total_tokens or 0,
        "total_cost": (usage_row.total_cost or 0) if usage_row.total_cost else 0.0,
        "active_models": usage_row.active_models or [],
        "last_activity": usage_row.last_activity.isoformat()
        if usage_row.last_activity
        else None,
        "budget_used": (usage_row.total_cost or 0) if usage_row.total_cost else 0.0,
        "budget_limit": (user.budget_limit),
        "rate_limit_usage": 0,  # 需要实时速率限制数据
        "rate_limit": user.rpm_limit,
    }


@router.get("/stats/usage-trend")
async def usage_trend(
    period: str = "7d",
    granularity: str = "day",
    model: Optional[str] = None,
    user_id: Optional[str] = None,
    db=Depends(get_db_session),
    cur_user=Depends(authenticate_user),
):
    """使用趋势统计"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, select

    # 计算时间范围
    if period == "7d":
        days = 7
    elif period == "30d":
        days = 30
    elif period == "90d":
        days = 90
    else:
        days = 7

    end_date = datetime.now() + timedelta(days=1)
    start_date = end_date - timedelta(days=days)

    # 权限：普通用户只能查看自己的数据；管理员可查看所有或指定用户
    if cur_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    if cur_user.get("role") != "admin":
        # 非管理员：如果指定了 user_id 必须是自己的 id，否则强制只看自己的数据
        if user_id and user_id != cur_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        user_id = cur_user.get("user_id")

    # 构建 where 条件（基于 CompletionLog）
    where_clauses = [
        CompletionLog.created_at >= start_date,
        CompletionLog.created_at <= end_date,
    ]
    if model:
        where_clauses.append(CompletionLog.model_name == model)
    if user_id:
        where_clauses.append(CompletionLog.user_id == user_id)

    # 查询所有符合条件的记录（在 Python 侧分组避免时区问题）
    stmt = select(
        CompletionLog.created_at,
        CompletionLog.user_id,
        CompletionLog.total_tokens,
        CompletionLog.cost,
    ).where(*where_clauses)

    result = await db.execute(stmt)
    stats_data = result.all()

    # 在 Python 侧按日期分组（避免 PostgreSQL 时区问题）
    from collections import defaultdict

    grouped = defaultdict(
        lambda: {"calls": 0, "tokens": 0, "cost": 0.0, "users": set()}
    )

    for stat in stats_data:
        created_at = stat[0]
        user_id = stat[1]
        tokens = stat[2] or 0
        cost = stat[3] or 0
        if created_at:
            if granularity == "day":
                date_key = created_at.strftime("%Y-%m-%d")
            elif granularity == "week":
                date_key = created_at.strftime("%Y-W%U")
            elif granularity == "month":
                date_key = created_at.strftime("%Y-%m")
            else:
                date_key = created_at.strftime("%Y-%m-%d")

            grouped[date_key]["calls"] += 1
            grouped[date_key]["tokens"] += int(tokens)
            grouped[date_key]["cost"] += float(cost)
            if user_id:
                grouped[date_key]["users"].add(user_id)

    # 格式化返回数据
    data = []
    for date_key in sorted(grouped.keys()):
        entry = grouped[date_key]
        data.append(
            {
                "date": date_key,
                "calls": entry["calls"],
                "tokens": entry["tokens"],
                "cost": entry["cost"],
                "users": len(entry["users"]),
            }
        )

    return {"period": period, "granularity": granularity, "data": data}


@router.get("/stats/user-trend")
async def user_trend(
    period: str = "7d",
    granularity: str = "day",
    model: Optional[str] = None,
    db=Depends(get_db_session),
    cur_user=Depends(authenticate_user),
):
    """用户使用趋势统计 - 按用户聚合"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, select

    # 根据粒度计算时间范围
    end_date = datetime.now()
    # 计算时间范围基于 period 参数而不是 granularity
    if period == "1d":
        days = 1
    elif period == "7d":
        days = 7
    elif period == "30d":
        days = 30
    elif period == "90d":
        days = 90
    elif period == "365d":
        days = 365
    else:
        days = 7  # 默认7天

    start_date = end_date - timedelta(days=days)

    # 权限：普通用户只能查看自己的数据；管理员可查看所有
    if cur_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    # 构建 where 条件
    where_clauses = [
        CompletionLog.created_at >= start_date,
        CompletionLog.created_at <= end_date,
    ]
    if model:
        where_clauses.append(CompletionLog.model_name == model)

    # 如果是非管理员用户，只查看自己的数据
    if cur_user.get("role") != "admin":
        where_clauses.append(CompletionLog.user_id == cur_user.get("user_id"))

    # 查询所有符合条件的记录（在 Python 侧分组避免时区问题）
    stmt = select(
        CompletionLog.user_id,
        CompletionLog.created_at,
        CompletionLog.total_tokens,
        CompletionLog.cost,
    ).where(*where_clauses)

    result = await db.execute(stmt)
    stats_data = result.all()

    # 获取用户信息
    user_ids = list(set([stat[0] for stat in stats_data if stat[0]]))
    user_map = {}
    if user_ids:
        user_stmt = select(User.id, User.username).where(User.id.in_(user_ids))
        user_result = await db.execute(user_stmt)
        user_map = {row.id: row.username for row in user_result.all()}

    # 在 Python 侧按用户和日期分组
    from collections import defaultdict

    grouped = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})

    for stat in stats_data:
        user_id = stat[0]
        created_at = stat[1]
        tokens = stat[2] or 0
        cost = stat[3] or 0
        if user_id and created_at:
            if granularity == "day":
                date_key = created_at.strftime("%Y-%m-%d")
            elif granularity == "week":
                date_key = created_at.strftime("%Y-W%U")
            elif granularity == "month":
                date_key = created_at.strftime("%Y-%m")
            else:
                date_key = created_at.strftime("%Y-%m-%d")

            key = (user_id, date_key)
            grouped[key]["calls"] += 1
            grouped[key]["tokens"] += int(tokens)
            grouped[key]["cost"] += float(cost)

    # 格式化返回数据
    data = []
    for (user_id, date_key), entry in sorted(grouped.items()):
        username = user_map.get(user_id, f"User {user_id[:8]}")
        data_entry = {
            "user_id": user_id,
            "username": username,
            "calls": entry["calls"],
            "tokens": entry["tokens"],
            "cost": entry["cost"],
        }
        if granularity == "day":
            data_entry["date"] = date_key
        elif granularity == "week":
            data_entry["week"] = date_key
        elif granularity == "month":
            data_entry["month"] = date_key
        data.append(data_entry)

    return {"period": period, "granularity": granularity, "data": data}


@router.get("/stats/model-trend")
async def model_trend(
    period: str = "7d",
    granularity: str = "day",
    user_id: Optional[str] = None,
    db=Depends(get_db_session),
    cur_user=Depends(authenticate_user),
):
    """模型调用趋势统计 - 按模型聚合"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, select

    # 计算时间范围
    if period == "1d":
        days = 1
    elif period == "7d":
        days = 7
    elif period == "30d":
        days = 30
    elif period == "90d":
        days = 90
    else:
        days = 7

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 权限：普通用户只能查看自己的数据；管理员可查看所有或指定用户
    if cur_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    if cur_user.get("role") != "admin":
        # 非管理员：如果指定了 user_id 必须是自己的 id，否则强制只看自己的数据
        if user_id and user_id != cur_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        user_id = cur_user.get("user_id")

    # 构建 where 条件
    where_clauses = [
        CompletionLog.created_at >= start_date,
        CompletionLog.created_at <= end_date,
    ]
    if user_id:
        where_clauses.append(CompletionLog.user_id == user_id)

    # 查询所有符合条件的记录（在 Python 侧分组避免时区问题）
    stmt = select(
        CompletionLog.model_name,
        CompletionLog.created_at,
        CompletionLog.total_tokens,
        CompletionLog.cost,
    ).where(*where_clauses)

    result = await db.execute(stmt)
    stats_data = result.all()

    # 在 Python 侧按模型和日期分组
    from collections import defaultdict

    grouped = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})

    for stat in stats_data:
        model_name = stat[0]
        created_at = stat[1]
        tokens = stat[2] or 0
        cost = stat[3] or 0
        if model_name and created_at:
            if granularity == "day":
                date_key = created_at.strftime("%Y-%m-%d")
            elif granularity == "week":
                date_key = created_at.strftime("%Y-W%U")
            elif granularity == "month":
                date_key = created_at.strftime("%Y-%m")
            else:
                date_key = created_at.strftime("%Y-%m-%d")

            key = (model_name, date_key)
            grouped[key]["calls"] += 1
            grouped[key]["tokens"] += int(tokens)
            grouped[key]["cost"] += float(cost)

    # 格式化返回数据
    data = []
    for (model_name, date_key), entry in sorted(grouped.items()):
        data_entry = {
            "model_name": model_name,
            "calls": entry["calls"],
            "tokens": entry["tokens"],
            "cost": entry["cost"],
        }
        if granularity == "day":
            data_entry["date"] = date_key
        elif granularity == "week":
            data_entry["week"] = date_key
        elif granularity == "month":
            data_entry["month"] = date_key
        data.append(data_entry)

    return {"period": period, "granularity": granularity, "data": data}
