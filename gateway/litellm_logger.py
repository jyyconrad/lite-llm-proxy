"""LiteLLM 自定义日志记录器

用于记录 LLM 请求的成功和失败事件，并将日志写入数据库。
"""
import asyncio
import json
import uuid
from typing import Any, Optional

from litellm.integrations.custom_logger import CustomLogger
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from .dependencies import get_logger, incr_rate_limit
from data import CompletionDetail, CompletionLog, UsageStat, sync_session


logger = get_logger()


def make_json_safe(obj: Any) -> Any:
    """将对象转换为 JSON 可序列化的格式

    Args:
        obj: 需要转换的对象

    Returns:
        JSON 可序列化的对象
    """
    # 基本类型直接返回
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # datetime 对象转为字符串
    if hasattr(obj, "isoformat"):
        return obj.isoformat()

    # dict
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}

    # list / tuple
    if isinstance(obj, (list, tuple)):
        return [make_json_safe(i) for i in obj]

    # Pydantic / LiteLLM object
    if hasattr(obj, "model_dump"):
        return make_json_safe(obj.model_dump())

    # 兜底：强制字符串
    return str(obj)


def _write_usage(uid: str, req_model:str,model: str, tokens: int, cost: float):
    """写入用量统计

    Args:
        uid: 用户 ID
        model: 模型名称
        tokens: 消耗的 token 数量
        cost: 花费成本
    """
    try:
        incr_rate_limit(uid, req_model, model, tokens, cost)
        sess = sync_session()

        stmt = (
            insert(UsageStat)
            .values(
                id=str(uuid.uuid4()),
                user_id=uid,
                model_name=req_model,
                request_count=1,
                total_tokens=tokens,
                total_cost=cost,
                last_used=func.now(),
            )
            .on_conflict_do_update(
                index_elements=["user_id", "model_name"],
                set_={
                    "request_count": UsageStat.request_count + 1,
                    "total_tokens": UsageStat.total_tokens + tokens,
                    "total_cost": UsageStat.total_cost + cost,
                    "last_used": func.now(),
                },
            )
        )

        sess.execute(stmt)
        sess.commit()
    except Exception as e:
        logger.error(f"[usage_stat_error] {e}")
    finally:
        sess.close()


def _write_completion_log(
    *,
    uid: str,
    model: str,
    request_data: dict,
    messages: list | None,
    tools: list | None,
    response_data: dict | None,
    full_response: list | dict | None,
    total_tokens: int,
    cost: float,
    status: str,
    error_message: str | None = None,
    duration: int = 0,
):
    """
    记录一次 completion 的完整日志（支持 stream / non-stream）

    Args:
        uid: 用户 ID
        model: 模型名称
        request_data: 请求数据
        messages: 消息列表
        tools: 工具列表
        response_data: 响应数据
        full_response: 完整响应
        total_tokens: 总 token 数量
        cost: 成本
        status: 状态（success/error）
        error_message: 错误消息
        duration: 耗时（毫秒）
    """
    try:
        sess = sync_session()

        # token 拆分（如果能拿到）
        request_tokens = 0
        response_tokens = 0
        if isinstance(full_response, dict) and "usage" in full_response:
            usage = full_response.get("usage") or {}
            request_tokens = usage.get("prompt_tokens", 0)
            response_tokens = usage.get("completion_tokens", 0)

        log_entry = CompletionLog(
            id=str(uuid.uuid4()),
            user_id=uid,
            model_name=model,
            request_data=make_json_safe(request_data),
            response_data=make_json_safe(response_data),
            request_tokens=request_tokens,
            response_tokens=response_tokens,
            total_tokens=total_tokens,
            cost=cost,
            status=status,
            error_message=str(error_message) if error_message else None,
            duration=duration,
        )
        sess.add(log_entry)
        sess.flush()

        detail_entry = CompletionDetail(
            completion_log_id=log_entry.id,
            messages=make_json_safe(messages),
            tools=make_json_safe(tools),
            full_response=make_json_safe(full_response),
        )
        sess.add(detail_entry)

        sess.commit()
        sess.close()

    except Exception as e:
        logger.error(f"[completion_log_error] {e}")


class LiteLLMCustomLogger(CustomLogger):
    """LiteLLM 自定义日志记录器

    用于记录 LLM 请求的成功和失败事件，并将日志写入数据库。
    """

    def __init__(self):
        super().__init__()
        self.logger = logger
    
    def log_usage(self, user_id: str, req_model:str,model:str, tokens: int, cost: float):
        loop = asyncio.get_event_loop()
        self.logger.info(f"{user_id},{req_model},{model},{tokens}")
        # 写入用量统计
        loop.create_task(
            asyncio.to_thread(_write_usage, user_id, req_model, model, tokens, cost)
        )

    def log_success_event(
        self,
        kwargs: dict,
        response_obj: Optional[Any] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> None:
        """记录成功事件（同步）

        Args:
            kwargs: 完成请求的关键字参数
            response_obj: 响应对象
            start_time: 开始时间
            end_time: 结束时间
        """
        try:
            duration = None
            if start_time and end_time:
                duration = end_time - start_time
                if hasattr(duration, "total_seconds"):
                    duration = duration.total_seconds()

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            user_id = kwargs.get("user_id")
            req_model = kwargs.get("req_model")
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            cost = 0.0
            extra_body = kwargs.get('extra_body', {})

            user_id=user_id if  user_id else extra_body.get("user_id","unknown")
            req_model=req_model if  req_model else extra_body.get("req_model",model)

            if response_obj and hasattr(response_obj, "usage"):
                usage = response_obj.usage
                if usage:
                    prompt_tokens = getattr(usage, "prompt_tokens", 0)
                    completion_tokens = getattr(usage, "completion_tokens", 0)
                    total_tokens = getattr(usage, "total_tokens", 0)
                    cost = getattr(usage, "completion_cost", 0.0)

            duration_ms = int(duration * 1000) if duration is not None else 0
            duration_str = f"duration: {duration:.2f}s" if duration is not None else ""

            self.logger.info(
                f"[LiteLLM] Success - model: {model}, "
                f"request_model: {req_model}, "
                f"messages: {len(messages)}, "
                f"uid: {user_id}, "
                f"tokens: {total_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens}), "
                f"{duration_str}"
            )

            # 异步写入数据库（不阻塞主流程）
            loop = asyncio.get_event_loop()
            req_data={
                "user_id": user_id,
                "model": req_model,
                "messages": messages,
                "tools": kwargs.get("tools", None),
            }
            loop.create_task(
                asyncio.to_thread(
                    _write_completion_log,
                    uid=user_id,
                    model=req_model,
                    request_data=req_data,
                    messages=messages,
                    tools=kwargs.get("tools", None),
                    response_data=None,
                    full_response=(
                        response_obj.model_dump() if hasattr(response_obj, "model_dump") else response_obj
                    ),
                    total_tokens=total_tokens,
                    cost=cost,
                    status="success",
                    error_message=None,
                    duration=duration_ms,
                )
            )

            # 写入用量统计
            loop.create_task(
                asyncio.to_thread(_write_usage, user_id, req_model,model, total_tokens, cost)
            )

        except Exception as e:
            self.logger.error(f"[LiteLLM] log_success_event error: {e}")

    def log_failure_event(
        self,
        kwargs: dict,
        response_obj: Optional[Any] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> None:
        """记录失败事件（同步）

        Args:
            kwargs: 完成请求的关键字参数
            response_obj: 响应对象
            start_time: 开始时间
            end_time: 结束时间
        """
        try:
            model = kwargs.get("model", "unknown")
            error = getattr(response_obj, "error", str(response_obj))
            duration = None
            if start_time and end_time:
                duration = end_time - start_time
                if hasattr(duration, "total_seconds"):
                    duration = duration.total_seconds()

            duration_ms = int(duration * 1000) if duration is not None else 0
            duration_str = f"duration: {duration:.2f}s" if duration is not None else ""

            self.logger.error(
                f"[LiteLLM] Failure - model: {model}, "
                f"error: {error}, "
                f"{duration_str}"
            )

            # 异步写入数据库（不阻塞主流程）
            loop = asyncio.get_event_loop()
            user_id = kwargs.get("user_id", "unknown")
            loop.create_task(
                asyncio.to_thread(
                    _write_completion_log,
                    uid=user_id,
                    model=model,
                    request_data=kwargs,
                    messages=kwargs.get("messages"),
                    tools=kwargs.get("tools"),
                    response_data=None,
                    full_response=None,
                    total_tokens=0,
                    cost=0.0,
                    status="error",
                    error_message=str(error),
                    duration=duration_ms,
                )
            )

        except Exception as e:
            self.logger.error(f"[LiteLLM] log_failure_event error: {e}")

    # 异步版本
    async def async_log_success_event(
        self,
        kwargs: dict,
        response_obj: Optional[Any] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> None:
        """异步记录成功事件"""
        self.log_success_event(kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(
        self,
        kwargs: dict,
        response_obj: Optional[Any] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> None:
        """异步记录失败事件"""
        self.log_failure_event(kwargs, response_obj, start_time, end_time)


# 创建自定义日志记录器实例
custom_logger = LiteLLMCustomLogger()
