# -*- coding: utf-8 -*-
"""
配置管理器，用于加载和缓存配置文件

支持双读机制：
1. 优先从数据库读取模型配置
2. 如果数据库中没有配置，回退到 YAML 文件
"""

from typing import Dict, Any, Optional, List, Union, Literal
import yaml
import os
import threading
import time
import warnings
from functools import lru_cache
from pydantic import BaseModel, Field, field_validator, model_validator
from data.model_info import ModelConfig, ModelInfoList, ModelEndPoint


# --------------------------------------------------------------------------- #
# 配置管理器
# --------------------------------------------------------------------------- #
class ConfigManager:
    """配置管理器，用于加载和缓存配置文件"""

    # 缓存 TTL（秒）
    CACHE_TTL = 60

    def __init__(self, config_path: str = "./litellm_config.yaml"):
        self.config_path = config_path
        self.config_cache: Dict[str, Any] = {}
        self.models_config: Dict[str, ModelConfig] = {}
        self.cache_lock = threading.Lock()
        self.last_modified = 0
        self.last_check_time = 0  # 上次检查文件修改的时间
        self.load_config()

    def _convert_legacy_model_config(
        self, model_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将旧格式的模型配置转换为 ModelConfig 兼容格式。
        支持旧格式（含 model_info）和新格式（单节点/多节点）。
        """
        # 如果已经包含 support_types 和 description，且 litellm_params 结构正确，则直接返回
        # 检查是否为旧格式（包含 model_info）
        if "model_info" in model_dict:
            # 旧格式转换
            model_info = model_dict.get("model_info", {})
            provider = model_info.get("provider", "openai")
            max_tokens = model_info.get("max_tokens", 4096)

            litellm_params = model_dict.get("litellm_params", {})
            # 确保 litellm_params 包含必要的字段
            if "model" not in litellm_params:
                litellm_params["model"] = model_dict["model_name"]
            if "api_key" not in litellm_params:
                litellm_params["api_key"] = ""
            if "base_url" not in litellm_params:
                litellm_params["base_url"] = ""
            if "weight" not in litellm_params:
                litellm_params["weight"] = 1
            if "max_tokens" not in litellm_params:
                litellm_params["max_tokens"] = max_tokens
            if "rpm" not in litellm_params:
                litellm_params["rpm"] = model_dict.get("rpm", 0)
            if "tpm" not in litellm_params:
                litellm_params["tpm"] = model_dict.get("tpm", 0)
            # 将 provider 放入 litellm_params
            if "provider" not in litellm_params:
                litellm_params["provider"] = provider

            # 构建新格式（不包含顶层的 provider）
            new_model_dict = {
                "model_name": model_dict["model_name"],
                "litellm_params": litellm_params,
                "rpm": model_dict.get("rpm", 0),
                "tpm": model_dict.get("tpm", 0),
                "max_tokens": max_tokens,
            }
            return new_model_dict

        # 新格式处理：确保缺失字段有默认值
        result = dict(model_dict)

        # 确保 support_types 存在
        if "support_types" not in result:
            result["support_types"] = ["text"]
        elif isinstance(result["support_types"], str):
            # 如果是字符串，转换为列表
            result["support_types"] = [result["support_types"]]

        # 确保 description 存在
        if "description" not in result:
            result["description"] = f"模型 {result['model_name']}"

        # 确保 default_rpm, default_tpm, default_max_tokens 存在
        if "default_rpm" not in result:
            result["default_rpm"] = 10
        if "default_tpm" not in result:
            result["default_tpm"] = 100000
        if "default_max_tokens" not in result:
            result["default_max_tokens"] = 32 * 1024

        # 处理 litellm_params
        litellm_params = result.get("litellm_params", {})
        # 如果顶层有 provider 字段，将其移动到 litellm_params（如果缺失）
        if "provider" in result and isinstance(litellm_params, dict):
            if "provider" not in litellm_params:
                litellm_params["provider"] = result["provider"]
            # 删除顶层的 provider 字段，因为 ModelConfig 不允许额外的字段
            del result["provider"]

        if isinstance(litellm_params, dict):
            # 检查是否包含 endpoints 键（多节点模式）
            if "endpoints" in litellm_params:
                # 多节点模式
                endpoints = litellm_params["endpoints"]
                if not isinstance(endpoints, list):
                    endpoints = [endpoints]
                # 确保每个端点有必要的字段
                for endpoint in endpoints:
                    if "provider" not in endpoint:
                        endpoint["provider"] = "openai"
                    if "weight" not in endpoint:
                        endpoint["weight"] = 1
                    if "max_tokens" not in endpoint:
                        endpoint["max_tokens"] = result["default_max_tokens"]
                    if "rpm" not in endpoint:
                        endpoint["rpm"] = result["default_rpm"]
                    if "tpm" not in endpoint:
                        endpoint["tpm"] = result["default_tpm"]
                litellm_params["endpoints"] = endpoints
            else:
                # 单节点模式
                if "provider" not in litellm_params:
                    litellm_params["provider"] = "openai"
                if "weight" not in litellm_params:
                    litellm_params["weight"] = 1
                if "max_tokens" not in litellm_params:
                    litellm_params["max_tokens"] = result["default_max_tokens"]
                if "rpm" not in litellm_params:
                    litellm_params["rpm"] = result["default_rpm"]
                if "tpm" not in litellm_params:
                    litellm_params["tpm"] = result["default_tpm"]
            result["litellm_params"] = litellm_params
        elif isinstance(litellm_params, list):
            # 多节点模式（endpoints 列表）
            for endpoint in litellm_params:
                if "provider" not in endpoint:
                    endpoint["provider"] = "openai"
                if "weight" not in endpoint:
                    endpoint["weight"] = 1
                if "max_tokens" not in endpoint:
                    endpoint["max_tokens"] = result["default_max_tokens"]
                if "rpm" not in endpoint:
                    endpoint["rpm"] = result["default_rpm"]
                if "tpm" not in endpoint:
                    endpoint["tpm"] = result["default_tpm"]
            result["litellm_params"] = {"endpoints": litellm_params}

        return result

    def load_config(self) -> None:
        """加载配置文件并缓存，使用 ModelConfig 验证"""
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Config file not found: {self.config_path}")

            # 检查文件是否被修改
            current_modified = os.path.getmtime(self.config_path)
            if current_modified <= self.last_modified:
                return  # 文件未被修改，无需重新加载

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            with self.cache_lock:
                self.config_cache = config
                # 提取模型配置并验证
                validated_models: Dict[str, ModelConfig] = {}
                for model in config.get("model_list", []):
                    try:
                        # 尝试转换为新格式
                        converted = self._convert_legacy_model_config(model)
                        # 使用 ModelConfig 验证
                        validated = ModelConfig.model_validate(converted)
                        validated_models[validated.model_name] = validated
                    except Exception as e:
                        warnings.warn(
                            f"模型配置验证失败 {model.get('model_name', 'unknown')}: {e}"
                        )
                        # 如果验证失败，跳过该模型，不加入配置
                        continue

                self.models_config = validated_models
                self.last_modified = current_modified

            print(f"Configuration loaded successfully from {self.config_path}")
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            raise

    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """获取指定模型的配置（仅从 YAML）"""
        with self.cache_lock:
            return self.models_config.get(model_name)

    def get_all_models(self) -> list:
        """获取所有模型名称（仅从 YAML）"""
        with self.cache_lock:
            return list(self.models_config.keys())

    def get_all_model_configs(self) -> Dict[str, ModelConfig]:
        """获取所有模型配置（仅从 YAML）"""
        with self.cache_lock:
            return self.models_config

    def refresh_if_needed(self) -> None:
        """如果配置文件有更新则刷新缓存（带时间间隔限制）"""
        try:
            current_time = time.time()

            # 每 CACHE_TTL 秒才检查一次文件修改时间
            if current_time - self.last_check_time < self.CACHE_TTL:
                return

            self.last_check_time = current_time
            current_modified = os.path.getmtime(self.config_path)
            if current_modified > self.last_modified:
                self.load_config()
        except Exception as e:
            print(f"Error checking config file modification: {str(e)}")

    def yaml_to_model_config(self, db_model_config: "DBModelConfig") -> Optional[ModelConfig]:
        """将数据库模型配置转换为 Pydantic ModelConfig"""
        from data.tables import ModelConfig as DBModelConfig

        litellm_params = db_model_config.litellm_params
        params = None

        if isinstance(litellm_params, dict):
            if "endpoints" in litellm_params:
                # 多节点模式 - 确保每个端点有必要的默认值
                endpoints_data = litellm_params.get("endpoints", [])
                endpoints_with_defaults = []
                for ep in endpoints_data:
                    endpoint = ModelEndPoint(
                        model=ep.get("model", ""),
                        api_key=ep.get("api_key", ""),
                        base_url=ep.get("base_url", ""),
                        provider=ep.get("provider", "openai"),
                        max_tokens=ep.get("max_tokens", 4096),
                        rpm=ep.get("rpm", 60),
                        tpm=ep.get("tpm", 100000),
                        weight=ep.get("weight", 1),
                    )
                    endpoints_with_defaults.append(endpoint)
                params = ModelInfoList(endpoints=endpoints_with_defaults)
            else:
                # 单节点模式 - 确保有必要的默认值
                params = ModelEndPoint(
                    model=litellm_params.get("model", ""),
                    api_key=litellm_params.get("api_key", ""),
                    base_url=litellm_params.get("base_url", ""),
                    provider=litellm_params.get("provider", "openai"),
                    max_tokens=litellm_params.get("max_tokens", 4096),
                    rpm=litellm_params.get("rpm", 60),
                    tpm=litellm_params.get("tpm", 100000),
                    weight=litellm_params.get("weight", 1),
                )

        return ModelConfig(
            model_name=db_model_config.model_name,
            litellm_params=params,
            support_types=db_model_config.support_types or ["text"],
            default_rpm=db_model_config.default_rpm,
            default_tpm=db_model_config.default_tpm,
            default_max_tokens=db_model_config.default_max_tokens,
            description=db_model_config.description,
        )


# 全局配置管理器实例
config_manager = ConfigManager()


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """获取模型配置的便捷函数（仅从 YAML）"""
    config_manager.refresh_if_needed()
    return config_manager.get_model_config(model_name)


def get_all_model_configs() -> Dict[str, ModelConfig]:
    """获取所有模型配置的便捷函数（仅从 YAML）"""
    config_manager.refresh_if_needed()
    return config_manager.get_all_model_configs()


def get_all_models() -> list:
    """获取所有模型的便捷函数（仅从 YAML）"""
    config_manager.refresh_if_needed()
    return config_manager.get_all_models()


# --------------------------------------------------------------------------- #
# 异步配置获取函数（支持数据库优先）
# --------------------------------------------------------------------------- #
async def async_get_model_config(
    model_name: str, db_session
) -> Optional[ModelConfig]:
    """异步获取模型配置，优先从数据库读取，fallback 到 YAML

    Args:
        model_name: 模型名称
        db_session: 数据库会话

    Returns:
        ModelConfig Pydantic 模型，如果都不存在则返回 None
    """
    from sqlalchemy import select
    from data.tables import ModelConfig as DBModelConfig

    # 优先从数据库获取
    try:
        stmt = select(DBModelConfig).where(
            DBModelConfig.model_name == model_name,
            DBModelConfig.is_active == True
        )
        result = await db_session.execute(stmt)
        db_config = result.scalars().first()

        if db_config is not None:
            # 数据库中有配置，转换为 Pydantic 模型
            litellm_params = db_config.litellm_params
            params = None

            if isinstance(litellm_params, dict):
                if "endpoints" in litellm_params:
                    # 多节点模式
                    params = ModelInfoList(**litellm_params)
                else:
                    # 单节点模式 - 确保有必要的默认值
                    params = ModelEndPoint(
                        model=litellm_params.get("model", ""),
                        api_key=litellm_params.get("api_key", ""),
                        base_url=litellm_params.get("base_url", ""),
                        provider=litellm_params.get("provider", "openai"),
                        max_tokens=litellm_params.get("max_tokens", 4096),
                        rpm=litellm_params.get("rpm", 60),
                        tpm=litellm_params.get("tpm", 100000),
                        weight=litellm_params.get("weight", 1),
                    )

            return ModelConfig(
                model_name=db_config.model_name,
                litellm_params=params,
                support_types=db_config.support_types or ["text"],
                default_rpm=db_config.default_rpm,
                default_tpm=db_config.default_tpm,
                default_max_tokens=db_config.default_max_tokens,
                description=db_config.description,
            )
    except Exception as e:
        # 数据库查询失败，记录警告并继续回退到 YAML
        warnings.warn(f"Database query failed, falling back to YAML: {e}")

    # 回退到 YAML 配置
    config_manager.refresh_if_needed()
    return config_manager.get_model_config(model_name)


async def async_get_all_models_with_db(
    db_session, include_inactive: bool = False
) -> List[str]:
    """获取所有模型名称，优先从数据库，合并 YAML

    Args:
        db_session: 数据库会话
        include_inactive: 是否包含已禁用的模型

    Returns:
        所有模型名称列表
    """
    from sqlalchemy import select
    from data.tables import ModelConfig as DBModelConfig

    yaml_models = set(config_manager.get_all_models())
    db_models = set()

    try:
        # 从数据库获取所有模型
        if include_inactive:
            stmt = select(DBModelConfig.model_name)
        else:
            stmt = select(DBModelConfig.model_name).where(
                DBModelConfig.is_active == True
            )

        result = await db_session.execute(stmt)
        db_models = {row[0] for row in result.all()}
    except Exception as e:
        warnings.warn(f"Database query for models failed: {e}")

    # 合并：数据库 + YAML
    all_models = list(db_models | yaml_models)
    return all_models


async def async_get_all_model_configs_with_db(
    db_session, include_inactive: bool = False
) -> Dict[str, ModelConfig]:
    """获取所有模型配置，优先从数据库，合并 YAML

    Args:
        db_session: 数据库会话
        include_inactive: 是否包含已禁用的模型

    Returns:
        模型名称到配置的字典
    """
    from sqlalchemy import select
    from data.tables import ModelConfig as DBModelConfig

    # 获取 YAML 配置
    yaml_configs = config_manager.get_all_model_configs()

    # 从数据库获取配置
    db_configs = {}
    try:
        if include_inactive:
            stmt = select(DBModelConfig)
        else:
            stmt = select(DBModelConfig).where(DBModelConfig.is_active == True)

        result = await db_session.execute(stmt)
        for db_config in result.scalars().all():
            yaml_configs[db_config.model_name] = config_manager.yaml_to_model_config(db_config)
    except Exception as e:
        warnings.warn(f"Database query for model configs failed: {e}")

    return yaml_configs
