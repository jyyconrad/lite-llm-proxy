# 标准库导入
import asyncio
import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

# 第三方库导入
import litellm
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from litellm import ModelResponse
from openai import OpenAI
from pydantic import BaseModel

# 本地模块导入
from ..config import get_settings
from ..dependencies import authenticate_user, check_rate_limit, get_logger, incr_concurrent, decr_concurrent
from ..local_model_manage import embedding_encode
from ..models import CompletionRequest, EmbeddingRequest
from ..litellm_logger import custom_logger
from ..resilience import (
    get_circuit_breaker,
    get_failover_manager,
    RetryConfig,
    calculate_retry_delay,
    CircuitBreakerConfig,
)
from config_manager import async_get_model_config, async_get_all_models_with_db
from data import CompletionDetail, CompletionLog, UsageStat, sync_session, get_db_session

logger = get_logger()


def _parse_arguments_if_json(arguments: Any) -> Any:
    if not isinstance(arguments, str):
        return arguments

    try:
        return json.loads(arguments)
    except (json.JSONDecodeError, ValueError):
        return arguments


def _process_function_calls(resp: Any) -> Any:
    if isinstance(resp, dict):
        choices = resp.get("choices", [])
        for choice in choices:
            message = choice.get("message", {})

            fc = message.get("function_call")
            if fc and isinstance(fc, dict):
                args = fc.get("arguments")
                if args is not None:
                    fc["arguments"] = _parse_arguments_if_json(args)

            tcs = message.get("tool_calls", [])
            for tc in tcs:
                if isinstance(tc, dict):
                    func = tc.get("function", {})
                    if isinstance(func, dict):
                        args = func.get("arguments")
                        if args is not None:
                            func["arguments"] = _parse_arguments_if_json(args)
    elif hasattr(resp, "model_dump"):
        data = resp.model_dump()
        return _process_function_calls(data)

    return resp


# ==================== 数据模型 ====================


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = ""


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


# ==================== Anthropic 消息模型 ====================


class AnthropicMessageContent(BaseModel):
    """Anthropic 消息内容块"""
    type: str = "text"
    text: Optional[str] = None


class AnthropicMessage(BaseModel):
    """Anthropic 消息格式"""
    role: str
    content: str


class AnthropicMessageRequest(BaseModel):
    """Anthropic 消息 API 请求格式

    对应 POST /v1/messages
    """
    model: str
    messages: List[AnthropicMessage] = []
    system: Optional[str] = None
    max_tokens: int = 4096
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None
    stream: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = None


class AnthropicUsage(BaseModel):
    """Anthropic 用量信息"""
    input_tokens: int
    output_tokens: int


class AnthropicContentBlock(BaseModel):
    """Anthropic 内容块"""
    type: str
    text: Optional[str] = None


class AnthropicMessageResponse(BaseModel):
    """Anthropic 消息 API 响应格式（非流式）"""
    id: str
    type: str = "message"
    role: str = "assistant"
    content: List[AnthropicContentBlock]
    model: str
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: AnthropicUsage


# ==================== 路由配置 ====================

router = APIRouter()

# 配置 LiteLLM 使用自定义日志记录器
litellm.set_verbose = False
litellm.callbacks = [custom_logger]

# 重试配置
retry_config = RetryConfig(max_retries=2, initial_delay=0.5, max_delay=5.0)


async def _call_llm_with_retry(params: dict, uid: str, req_model: str, is_stream: bool):
    """使用重试机制调用 LLM"""
    import asyncio

    # 获取或创建熔断器
    model_name = params.get("model", "unknown")
    cb = get_circuit_breaker(model_name)

    last_error = None

    for attempt in range(retry_config.max_retries + 1):
        # 检查熔断器状态
        if not cb.can_execute():
            logger.warning(
                f"Circuit breaker open for {model_name}, attempt {attempt + 1}"
            )
            if attempt < retry_config.max_retries:
                await asyncio.sleep(calculate_retry_delay(attempt, retry_config))
                continue
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable (circuit breaker open)",
            )

        try:
            if is_stream:
                return await litellm.acompletion(
                    **params, max_retries=0, user_id=uid, req_model=req_model
                )
            else:
                return await litellm.acompletion(
                    **params, max_retries=0, user_id=uid, req_model=req_model
                )
        except Exception as e:
            cb.record_failure()
            last_error = e
            logger.warning(
                f"LLM call failed (attempt {attempt + 1}/{retry_config.max_retries + 1}): {e}"
            )

            if attempt < retry_config.max_retries:
                delay = calculate_retry_delay(attempt, retry_config)
                await asyncio.sleep(delay)
            continue

    cb.record_failure()
    raise last_error


@router.post("/chat/completions")
async def completions(
    req: CompletionRequest,
    u=Depends(authenticate_user),
    db=Depends(get_db_session),
):
    """Chat Completions API

    兼容 OpenAI 的 `/v1/chat/completions` 端点。

    Args:
        req: Completion 请求数据
        u: 认证用户信息
        db: 数据库会话

    Returns:
        流式或非流式响应

    Raises:
        HTTPException: 当模型不存在或无可用端点时
    """
    logger.info(f"Completions request from user {u['user_id']} for model {req.model}")

    cfg = await async_get_model_config(req.model, db)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"Model {req.model} not found")

    endpoint = await check_rate_limit(u, cfg)

    if endpoint is None:
        raise HTTPException(status_code=500, detail="没有可用模型")

    uid = u["user_id"]
    model = endpoint.model
    api_key = endpoint.api_key
    base_url = endpoint.base_url
    max_tokens = min(cfg.default_max_tokens, endpoint.max_tokens or 999999)
    provider = endpoint.provider

    params = {
        **req.model_dump(exclude_none=True),
        "model": f"{endpoint.provider}/{model}",
        "api_key": api_key,
        "base_url": base_url,
        "max_tokens": max_tokens,
        "stream": req.stream,
    }
    if params.get("stream"):
        # 流式响应 - 使用重试机制
        await incr_concurrent(req.model)
        await incr_concurrent("global")
        stream = None
        try:
            stream = await _call_llm_with_retry(params, uid, req.model, True)
        except Exception as e:
            await decr_concurrent(req.model)
            await decr_concurrent("global")
            raise
        full_response_chunks = []
        start_time = asyncio.get_event_loop().time()
        prompt_tokens = 0
        completion_tokens = 0
        completion_content = ""

        async def generate():
            nonlocal full_response_chunks, start_time, prompt_tokens, completion_tokens, completion_content
            try:
                async for chunk in stream:
                    processed_chunk = _process_function_calls(chunk)
                    full_response_chunks.append(processed_chunk)

                    # 尝试从 chunk 累积 tokens
                    if hasattr(chunk, 'usage') and chunk.usage:
                        prompt_tokens = getattr(chunk.usage, 'prompt_tokens', 0)
                        completion_tokens += getattr(chunk.usage, 'completion_tokens', 0)

                    chunk_str = (
                        processed_chunk.model_dump_json(ensure_ascii=False)
                        if hasattr(processed_chunk, "model_dump_json")
                        else json.dumps(processed_chunk, ensure_ascii=False)
                    )
                    yield f"data: {chunk_str}\n\n"
            except Exception as e:
                logger.error(f"Stream error: {e}")
                error_msg = str(e).replace('"', '\\"')
                error_data = json.dumps({"error": {"message": error_msg}}, ensure_ascii=False)
                yield f"data: {error_data}\n\n"

                # 记录错误日志
                custom_logger.log_failure_event(
                    kwargs=params,
                    response_obj=e,
                    start_time=start_time,
                    end_time=asyncio.get_event_loop().time()
                )
            finally:
                # 减少并发计数
                await decr_concurrent(req.model)
                await decr_concurrent("global")
                yield "data: [DONE]\n\n"

                # 流结束时统一保存日志
                if len(full_response_chunks) > 0:
                    # 将所有chunk转为可序列化格式
                    chunks_data = [
                        chunk.model_dump() if hasattr(chunk, "model_dump") else chunk
                        for chunk in full_response_chunks
                    ]

                    # 计算总 tokens
                    total_tokens = prompt_tokens + completion_tokens

                    # 估算 completion tokens（基于字符）
                    estimated_completion_tokens = len(completion_content) // 4

                    # 构造响应对象
                    response_obj = type('StreamResponse', (), {
                        'usage': type('Usage', (), {
                            'prompt_tokens': prompt_tokens,
                            'completion_tokens': completion_tokens if completion_tokens > 0 else estimated_completion_tokens,
                            'total_tokens': total_tokens if total_tokens > 0 else prompt_tokens + estimated_completion_tokens,
                            'completion_cost': 0.0
                        })(),
                        'model_dump': lambda: {
                            'id': full_response_chunks[0].id if hasattr(full_response_chunks[0], 'id') else f"chatcmpl-{uuid.uuid4().hex[:24]}",
                            'object': 'chat.completion.chunk',
                            'created': int(time.time()),
                            'model': req.model,
                            'choices': [],
                            'chunks': chunks_data
                        }
                    })()

                    # 记录成功日志
                    custom_logger.log_success_event(
                        kwargs=params,
                        response_obj=response_obj,
                        start_time=start_time,
                        end_time=asyncio.get_event_loop().time()
                    )

        return StreamingResponse(generate(), media_type="text/event-stream; charset=utf-8")

    # 非流式响应 - 使用重试机制
    start_time_non_stream = asyncio.get_event_loop().time()
    await incr_concurrent(req.model)
    await incr_concurrent("global")
    try:
        resp = await _call_llm_with_retry(params, uid, req.model, False)
    finally:
        await decr_concurrent(req.model)
        await decr_concurrent("global")
    end_time_non_stream = asyncio.get_event_loop().time()

    # 确保响应对象有正确的 usage 属性
    if hasattr(resp, 'usage') and resp.usage:
        custom_logger.log_success_event(
            kwargs=params,
            response_obj=resp,
            start_time=start_time_non_stream,
            end_time=end_time_non_stream
        )

    return _process_function_calls(resp)


@router.get("/models", response_model=ModelListResponse)
async def list_models(db=Depends(get_db_session)):
    """列出所有可用的模型

    Returns:
        ModelListResponse: 包含所有可用模型的列表
    """
    model_names = await async_get_all_models_with_db(db)
    model_data = [
        ModelInfo(id=model_name, object="model", created=0, owned_by="")
        for model_name in model_names
    ]

    return ModelListResponse(data=model_data)


@router.post("/embeddings")
async def embeddings(
    req: EmbeddingRequest,
    u=Depends(authenticate_user),
    db=Depends(get_db_session),
):
    """Embeddings API

    兼容 OpenAI 的 `/v1/embeddings` 端点。

    Args:
        req: Embedding 请求数据
        u: 认证用户信息
        db: 数据库会话

    Returns:
        Embedding 响应

    Raises:
        HTTPException: 当模型不存在或请求失败时
    """
    logger.info(f"embedding request from user {u['user_id']} for model {req.model}")

    cfg = await async_get_model_config(req.model, db)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"Model {req.model} not found")

    endpoint = await check_rate_limit(u, cfg)

    if endpoint is None:
        raise HTTPException(status_code=500, detail="没有可用模型")

    model = endpoint.model
    api_key = endpoint.api_key
    base_url = endpoint.base_url
    provider = endpoint.provider
    tokens = 0
    params = {
        **req.model_dump(exclude_none=True),
        "model": f"{model}",
        "input": req.input,
        # "api_key":api_key,
        # "api_base":base_url
    }

    try:
        if provider == "local":
            resp = embedding_encode(
                req.model, req.input if isinstance(req.input, list) else [req.input]
            )

        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            resp = client.embeddings.create(**params)

    except Exception as e:
        logger.error(
            f"embeddings error for user {u['user_id']}, model {req.model}: {e}"
        )
        logger.error(e)
        raise HTTPException(500, f"embeddings error: {e}")
    finally:
        custom_logger.log_usage(
            user_id=u["user_id"],
            req_model=req.model,
            model=model,
            tokens=tokens,
            cost=0,
        )
    return resp


# ==================== Anthropic 消息 API ====================


def _convert_anthropic_to_openai_messages(
    anthropic_messages: List[AnthropicMessage],
    system: Optional[str] = None
) -> List[Dict[str, Any]]:
    """将 Anthropic 消息格式转换为 OpenAI 格式

    Args:
        anthropic_messages: Anthropic 消息列表
        system: 系统消息

    Returns:
        OpenAI 格式的消息列表
    """
    messages = []

    # 添加系统消息
    if system:
        messages.append({"role": "system", "content": system})

    # 转换用户和助手消息
    for msg in anthropic_messages:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })

    return messages


def _convert_openai_to_anthropic_response(
    response: Any,
    req_model: str
) -> AnthropicMessageResponse:
    """将 OpenAI 格式响应转换为 Anthropic 格式

    Args:
        response: OpenAI 格式响应
        req_model: 请求的模型名称

    Returns:
        Anthropic 格式响应
    """
    # 提取响应内容
    if hasattr(response, "choices") and response.choices:
        choice = response.choices[0]
        message = choice.message if hasattr(choice, "message") else choice

        # 获取 content
        content = ""
        if hasattr(message, "content") and message.content:
            content = message.content
        elif hasattr(message, "text") and message.text:
            content = message.text

        # 获取 stop_reason
        stop_reason = None
        if hasattr(choice, "finish_reason"):
            finish_reason = choice.finish_reason
            if finish_reason == "stop":
                stop_reason = "end_turn"
            elif finish_reason == "length":
                stop_reason = "max_tokens"
            elif finish_reason == "tool_calls":
                stop_reason = "tool_use"
            else:
                stop_reason = finish_reason
    else:
        content = ""

    # 提取 usage
    input_tokens = 0
    output_tokens = 0
    if hasattr(response, "usage") and response.usage:
        input_tokens = getattr(response.usage, "prompt_tokens", 0)
        output_tokens = getattr(response.usage, "completion_tokens", 0)

    # 生成响应 ID
    response_id = getattr(response, "id", f"msg_{uuid.uuid4().hex[:24]}")

    return AnthropicMessageResponse(
        id=response_id,
        type="message",
        role="assistant",
        content=[AnthropicContentBlock(type="text", text=content)],
        model=req_model,
        stop_reason=stop_reason,
        usage=AnthropicUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
    )


def _convert_openai_to_anthropic_stream_chunk(chunk: Any) -> Optional[str]:
    """将 OpenAI 流式 chunk 转换为 Anthropic 格式

    Args:
        chunk: OpenAI 流式 chunk

    Returns:
        Anthropic 格式的 SSE 行，如果应该跳过则返回 None
    """
    if not hasattr(chunk, "choices") or not chunk.choices:
        return None

    choice = chunk.choices[0]

    # 获取 delta 内容
    delta = getattr(choice, "delta", None)
    if not delta:
        return None

    content = ""
    if hasattr(delta, "content") and delta.content:
        content = delta.content
    elif hasattr(delta, "text") and delta.text:
        content = delta.text

    if not content:
        return None

    # 构建 Anthropic 事件
    event_data = {
        "type": "content_block_delta",
        "index": 0,
        "delta": {
            "type": "text_delta",
            "text": content
        }
    }

    return f"event: content_block_delta\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"


@router.post("/v1/messages")
async def create_message(
    req: AnthropicMessageRequest,
    u=Depends(authenticate_user),
    db=Depends(get_db_session),
):
    """Anthropic 兼容的消息 API

    对应 POST /v1/messages，支持 Claude 等模型。

    Args:
        req: AnthropicMessageRequest 请求数据
        u: 认证用户信息
        db: 数据库会话

    Returns:
        流式或非流式响应
    """
    logger.info(f"Anthropic messages request from user {u['user_id']} for model {req.model}")

    cfg = await async_get_model_config(req.model, db)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"Model {req.model} not found")

    endpoint = await check_rate_limit(u, cfg)

    if endpoint is None:
        raise HTTPException(status_code=500, detail="没有可用模型")

    uid = u["user_id"]
    model = endpoint.model
    api_key = endpoint.api_key
    base_url = endpoint.base_url
    max_tokens = min(cfg.default_max_tokens, endpoint.max_tokens or 999999, req.max_tokens)

    # 将 Anthropic 格式转换为 OpenAI 格式
    openai_messages = _convert_anthropic_to_openai_messages(req.messages, req.system)

    # 构建 LiteLLM 参数
    params = {
        "model": f"{endpoint.provider}/{model}",
        "messages": openai_messages,
        "api_key": api_key,
        "base_url": base_url,
        "max_tokens": max_tokens,
        "stream": req.stream or False,
    }

    # 添加可选参数
    if req.temperature is not None:
        params["temperature"] = req.temperature
    if req.top_p is not None:
        params["top_p"] = req.top_p
    if req.top_k is not None:
        params["top_k"] = req.top_k
    if req.stop_sequences is not None:
        params["stop"] = req.stop_sequences
    if req.tools is not None:
        params["tools"] = req.tools
    if req.tool_choice is not None:
        params["tool_choice"] = req.tool_choice

    if params.get("stream"):
        # 流式响应
        stream = await _call_llm_with_retry(params, uid, req.model, True)
        start_time = asyncio.get_event_loop().time()

        async def generate():
            try:
                input_tokens = 0
                output_tokens = 0
                content_text = ""

                async for chunk in stream:
                    # 尝试累积 tokens
                    if hasattr(chunk, 'usage') and chunk.usage:
                        input_tokens = getattr(chunk.usage, 'prompt_tokens', 0)
                        output_tokens += getattr(chunk.usage, 'completion_tokens', 0)

                    # 转换并发送 chunk
                    anthropic_line = _convert_openai_to_anthropic_stream_chunk(chunk)
                    if anthropic_line:
                        yield anthropic_line
                        # 累积内容用于日志
                        if hasattr(chunk, "choices") and chunk.choices:
                            choice = chunk.choices[0]
                            delta = getattr(choice, "delta", None)
                            if delta and hasattr(delta, "content"):
                                content_text += delta.content

                # 发送消息停止事件
                stop_event = {
                    "type": "message_stop",
                    "message": {
                        "id": f"msg_{uuid.uuid4().hex[:24]}",
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": req.model,
                        "stop_reason": "end_turn",
                        "stop_sequence": None,
                        "usage": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens
                        }
                    }
                }
                yield f"event: message_stop\ndata: {json.dumps(stop_event, ensure_ascii=False)}\n\n"

                # 发送 ping 事件
                yield f"event: ping\ndata: {{}}\n\n"

            except Exception as e:
                logger.error(f"Stream error: {e}")
                error_event = {
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": str(e)
                    }
                }
                yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream; charset=utf-8")

    # 非流式响应
    start_time = asyncio.get_event_loop().time()
    resp = await _call_llm_with_retry(params, uid, req.model, False)
    end_time = asyncio.get_event_loop().time()

    # 记录成功日志
    custom_logger.log_success_event(
        kwargs=params,
        response_obj=resp,
        start_time=start_time,
        end_time=end_time
    )

    # 转换为 Anthropic 格式
    anthropic_resp = _convert_openai_to_anthropic_response(resp, req.model)

    return anthropic_resp
