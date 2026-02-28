# -*- coding: utf-8 -*-
"""
配置管理器，用于加载和缓存配置文件
"""
from typing import Dict, Any, Optional, List, Union, Literal
import yaml
import os
import threading
import warnings
from pydantic import BaseModel, Field, field_validator, model_validator
from data.model_info import ModelConfig,  ModelInfoList, ModelEndPoint
# --------------------------------------------------------------------------- #
# 配置管理器
# --------------------------------------------------------------------------- #
class ConfigManager:
    """配置管理器，用于加载和缓存配置文件"""
    
    def __init__(self, config_path: str = "./litellm_config.yaml"):
        self.config_path = config_path
        self.config_cache: Dict[str, Any] = {}
        self.models_config: Dict[str, ModelConfig] = {}
        self.cache_lock = threading.Lock()
        self.last_modified = 0
        self.load_config()
        
    def _convert_legacy_model_config(self, model_dict: Dict[str, Any]) -> Dict[str, Any]:
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
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            with self.cache_lock:
                self.config_cache = config
                # 提取模型配置并验证
                validated_models: Dict[str, ModelConfig] = {}
                for model in config.get('model_list', []):
                    try:
                        # 尝试转换为新格式
                        converted = self._convert_legacy_model_config(model)
                        # 使用 ModelConfig 验证
                        validated = ModelConfig.model_validate(converted)
                        validated_models[validated.model_name] = validated
                    except Exception as e:
                        warnings.warn(f"模型配置验证失败 {model.get('model_name', 'unknown')}: {e}")
                        # 如果验证失败，跳过该模型，不加入配置
                        continue
                
                self.models_config = validated_models
                self.last_modified = current_modified
                
            print(f"Configuration loaded successfully from {self.config_path}")
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            raise
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """获取指定模型的配置"""
        with self.cache_lock:
            return self.models_config.get(model_name)
    
    def get_all_models(self) -> list:
        """获取所有模型名称"""
        with self.cache_lock:
            return list(self.models_config.keys())
    
    def get_all_model_configs(self) -> Dict[str, ModelConfig]:
        """获取所有模型配置"""
        with self.cache_lock:
            return self.models_config
    
    def refresh_if_needed(self) -> None:
        """如果配置文件有更新则刷新缓存"""
        try:
            current_modified = os.path.getmtime(self.config_path)
            if current_modified > self.last_modified:
                self.load_config()
        except Exception as e:
            print(f"Error checking config file modification: {str(e)}")

# 全局配置管理器实例
config_manager = ConfigManager()

def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """获取模型配置的便捷函数"""
    config_manager.refresh_if_needed()
    return config_manager.get_model_config(model_name)

def get_all_model_configs() -> Dict[str, ModelConfig]:
    """获取所有模型配置的便捷函数"""
    config_manager.refresh_if_needed()
    return config_manager.get_all_model_configs()

def get_all_models() -> list:
    """获取所有模型的便捷函数"""
    config_manager.refresh_if_needed()
    return config_manager.get_all_models()