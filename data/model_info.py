# -*- coding: utf-8 -*-
"""
litellm 路由层模型配置模型

本模块统一描述“一个模型”在 litellm 中的完整转发信息，
支持：
1. 单节点模式（ModelInfoDict）
2. 多节点负载均衡模式（ModelInfoList）

用法示例见各 class 的 `model_config` 中的 json_schema_extra。
"""
from typing import List, Literal, Union, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# --------------------------------------------------------------------------- #
# 单节点描述
# --------------------------------------------------------------------------- #
class ModelEndPoint(BaseModel):
    """
    单条模型转发节点信息。

    在“多节点”模式下，litellm 会按照 weight 做加权轮询；
    在“单节点”模式下，本类被直接复用。
    """
    model: str = Field(
        ...,
        description="模型全称，用于 litellm 路由，例如 gpt-4-turbo-2024-04-09",
        json_schema_extra={"example": "gpt-4-turbo"},
    )
    api_key: str = Field(
        ...,
        description="模型供应商的 API Key，支持环境变量注入，例如 ${OPENAI_API_KEY}",
        json_schema_extra={"example": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},
    )
    base_url: str = Field(
        ...,
        description="模型协议入口，必须带协议头，末尾无 /",
        json_schema_extra={"example": "https://api.openai.com/v1"},
    )
    weight: int = Field(
        default=1,
        ge=0,
        description="负载均衡权重，越大越优先；单节点模式下无意义,等于0时则不使用",
    )
    max_tokens: Optional[int] = Field(
        ...,
        gt=0,
        description="单次请求最大 token 上限（prompt + completion）",
        json_schema_extra={"example": 4096},
    )
    rpm: int = Field(
        ...,
        ge=0,
        description="Request-Per-Minute 限流，0 表示不限",
        json_schema_extra={"example": 60},
    )
    tpm: int = Field(
        ...,
        ge=0,
        description="Token-Per-Minute 限流，0 表示不限",
        json_schema_extra={"example": 100_000},
    )
    dimensions: Optional[int] = Field(
        default=None,
        description="向量模型维度",
        json_schema_extra={"example": 100_000},
    )
    provider: Optional[Literal["openai", "azure", "anthropic", "gemini", "custom", "local", "ollama"]] = Field(
        ...,
        description="供应商名称，用来选择底层 adapter",
        json_schema_extra={"example": "openai"},
    )
# --------------------------------------------------------------------------- #
# 多节点列表
# --------------------------------------------------------------------------- #
class ModelInfoList(BaseModel):
    endpoints: List[ModelEndPoint] = Field(
        ...,
        min_length=2,
        description="至少提供 2 个节点，系统按 weight 做加权轮询",
    )

# --------------------------------------------------------------------------- #
# 顶层配置：供 litellm 加载
# --------------------------------------------------------------------------- #
class ModelConfig(BaseModel):
    """
    最终写入 litellm 配置文件的条目。

    必须指定 model_name（对外暴露的名称）与 provider，
    并根据场景选择 `ModelInfoList` 或 `ModelInfoDict`。
    """
    model_name: str = Field(
        ...,
        description="用户侧看到的模型名称，可带自定义后缀，例如 gpt-4-turbo-cn",
        json_schema_extra={"example": "gpt-4-turbo-cn"},
    )
    support_types: List[Literal["text", "image","embedding"]] = Field(default=["text"],description="模型的类型")
    litellm_params: Union[ModelInfoList, ModelEndPoint] = Field(
        ...,
        description="节点信息，支持单节点或多节点",
    )
    default_rpm: int = Field(
        default=10,
        ge=0,
        description="rpm 限制，每分钟限制的请求数量，优先级高于节点自身 rpm",
    )
    default_tpm: int = Field(
        default=100000,
        ge=-1,
        description="tpm上线，每分钟限制的tokens数量，优先级高于节点自身 tpm",
    )
    default_max_tokens: int = Field(
        default=32*1024,
        ge=0,
        description="最大token上限，优先级高于节点自身 max_tokens",
    )
    description: str = Field(
        default="大语言模型",
        description="模型描述",
    )

    @model_validator(mode="after")
    def _sync_limits(self) -> "ModelConfig":
        """
        如果全局限流比节点里“最严格”的值还宽松，给出警告
        （也可以直接 raise，视业务而定）
        """
        params = self.litellm_params
        if isinstance(params, ModelInfoList):
            min_rpm = min(ep.rpm for ep in params.endpoints)
            min_tpm = min(ep.tpm for ep in params.endpoints)
            min_tokens = min(ep.max_tokens for ep in params.endpoints)
        else:
            min_rpm = params.rpm
            min_tpm = params.tpm
            min_tokens = params.max_tokens

        if self.default_rpm and self.default_rpm > min_rpm:
            import warnings
            warnings.warn(f"全局 rpm({self.default_rpm}) > 节点最小 rpm({min_rpm})，可能导致限流失效")
        if self.default_tpm and self.default_tpm > min_tpm:
            warnings.warn(f"全局 tpm({self.default_tpm}) > 节点最小 tpm({min_tpm})，可能导致限流失效")
        if self.default_max_tokens > min_tokens:
            warnings.warn(f"全局 max_tokens({self.default_max_tokens}) > 节点最小 max_tokens({min_tokens})，可能导致截断异常")
        return self

    class Config:
        # 让 pydantic 2.x 也能用 discriminator 自动反序列化
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "model_name": "gpt-4-turbo-cn",
                "provider": "openai",
                "rpm": 100,
                "tpm": 200_000,
                "max_tokens": 8192,
                "litellm_params": {
                    "model": "gpt-4-turbo",
                    "endpoints": [
                        {
                            "api_key": "${OPENAI_API_KEY}",
                            "base_url": "https://api.openai.com/v1",
                            "weight": 2,
                            "max_tokens": 8192,
                            "rpm": 60,
                            "tpm": 100_000,
                        },
                        {
                            "api_key": "${OPENAI_API_KEY_BACKUP}",
                            "base_url": "https://api.openai.com/v1",
                            "weight": 1,
                            "max_tokens": 8192,
                            "rpm": 60,
                            "tpm": 100_000,
                        },
                    ],
                },
            }
        }