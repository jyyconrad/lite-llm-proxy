# 标准库导入
import json
from typing import Any, AsyncGenerator, Optional

# 第三方库导入
import litellm
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from litellm import ModelResponse
from openai import OpenAI
from pydantic import BaseModel

# 本地模块导入
from ..config import get_settings
from ..dependencies import authenticate_user, check_rate_limit, get_logger
from ..local_model_manage import embedding_encode
from ..models import CompletionRequest, EmbeddingRequest
from ..litellm_logger import custom_logger
from config_manager import get_all_models, get_model_config
from data import CompletionDetail, CompletionLog, UsageStat, sync_session

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


# ==================== 路由配置 ====================

router = APIRouter()

# 配置 LiteLLM 使用自定义日志记录器
litellm.set_verbose = False
litellm.callbacks = [custom_logger]


@router.post("/chat/completions")
async def completions(req: CompletionRequest, u=Depends(authenticate_user)):
    """Chat Completions API

    兼容 OpenAI 的 `/v1/chat/completions` 端点。

    Args:
        req: Completion 请求数据
        u: 认证用户信息

    Returns:
        流式或非流式响应

    Raises:
        HTTPException: 当模型不存在或无可用端点时
    """
    logger.info(f"Completions request from user {u['user_id']} for model {req.model}")

    cfg = get_model_config(req.model)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"Model {req.model} not found")

    endpoint = await check_rate_limit(u, cfg)

    if endpoint is None:
        raise HTTPException(status_code=500, detail="没有可用模型")

    uid = u["user_id"]
    model = endpoint.model
    api_key = endpoint.api_key
    base_url = endpoint.base_url
    max_tokens = min(cfg.default_max_tokens, endpoint.max_tokens)
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
        # 流式响应 - 在异步环境中使用 acompletion
        stream = await litellm.acompletion(
            **params, max_retries=0, user_id=uid, req_model=req.model
        )

        async def generate():
            async for chunk in stream:
                processed_chunk = _process_function_calls(chunk)
                chunk_str = (
                    processed_chunk.model_dump_json()
                    if hasattr(processed_chunk, "model_dump_json")
                    else json.dumps(processed_chunk)
                )
                yield f"data: {chunk_str}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    resp = await litellm.acompletion(
        **params, max_retries=0, user_id=uid, req_model=req.model
    )
    return _process_function_calls(resp)


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    """列出所有可用的模型

    Returns:
        ModelListResponse: 包含所有可用模型的列表
    """
    model_names = get_all_models()
    model_data = [
        ModelInfo(id=model_name, object="model", created=0, owned_by="")
        for model_name in model_names
    ]

    return ModelListResponse(data=model_data)


@router.post("/embeddings")
async def embeddings(req: EmbeddingRequest, u=Depends(authenticate_user)):
    """Embeddings API

    兼容 OpenAI 的 `/v1/embeddings` 端点。

    Args:
        req: Embedding 请求数据
        u: 认证用户信息

    Returns:
        Embedding 响应

    Raises:
        HTTPException: 当模型不存在或请求失败时
    """
    logger.info(f"embedding request from user {u['user_id']} for model {req.model}")

    cfg = get_model_config(req.model)
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
