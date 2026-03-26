# -*- coding: utf-8 -*-
"""
测试模型配置默认值处理

针对模型配置 404 问题的修复验证测试。
根因：config_manager.py 中的 async_get_model_config 函数从数据库读取配置后，
实例化 ModelEndPoint 时缺少默认值处理，导致字段缺失时验证失败。

修复：使用 .get() 方法提供默认值。
"""

import pytest
import asyncio
import warnings
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

# 导入被测试的模块
from data.model_info import ModelConfig, ModelEndPoint, ModelInfoList
from config_manager import ConfigManager


class TestModelEndPointDefaults:
    """测试 ModelEndPoint 的默认值处理"""

    def test_complete_config(self):
        """测试完整配置正常实例化"""
        litellm_params = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'sk-test',
            'base_url': 'https://api.openai.com/v1',
            'provider': 'openai',
            'max_tokens': 4096,
            'rpm': 60,
            'tpm': 100000,
            'weight': 1
        }

        params = ModelEndPoint(
            model=litellm_params.get('model', ''),
            api_key=litellm_params.get('api_key', ''),
            base_url=litellm_params.get('base_url', ''),
            provider=litellm_params.get('provider', 'openai'),
            max_tokens=litellm_params.get('max_tokens', 4096),
            rpm=litellm_params.get('rpm', 60),
            tpm=litellm_params.get('tpm', 100000),
            weight=litellm_params.get('weight', 1),
        )

        assert params.model == 'gpt-3.5-turbo'
        assert params.api_key == 'sk-test'
        assert params.base_url == 'https://api.openai.com/v1'
        assert params.provider == 'openai'
        assert params.max_tokens == 4096
        assert params.rpm == 60
        assert params.tpm == 100000
        assert params.weight == 1

    def test_missing_dimensions(self):
        """测试缺少 dimensions 字段（可选字段）"""
        litellm_params = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'sk-test',
            'base_url': 'https://api.openai.com/v1',
            'provider': 'openai',
            'max_tokens': 4096,
            'rpm': 60,
            'tpm': 100000,
            'weight': 1
            # 缺少 dimensions
        }

        params = ModelEndPoint(
            model=litellm_params.get('model', ''),
            api_key=litellm_params.get('api_key', ''),
            base_url=litellm_params.get('base_url', ''),
            provider=litellm_params.get('provider', 'openai'),
            max_tokens=litellm_params.get('max_tokens', 4096),
            rpm=litellm_params.get('rpm', 60),
            tpm=litellm_params.get('tpm', 100000),
            weight=litellm_params.get('weight', 1),
        )

        assert params.model == 'gpt-3.5-turbo'
        assert params.dimensions is None  # 可选字段默认为 None

    def test_missing_optional_fields(self):
        """测试缺少多个可选字段"""
        litellm_params = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'sk-test',
            # 缺少 base_url, provider, max_tokens 等
        }

        params = ModelEndPoint(
            model=litellm_params.get('model', ''),
            api_key=litellm_params.get('api_key', ''),
            base_url=litellm_params.get('base_url', ''),
            provider=litellm_params.get('provider', 'openai'),
            max_tokens=litellm_params.get('max_tokens', 4096),
            rpm=litellm_params.get('rpm', 60),
            tpm=litellm_params.get('tpm', 100000),
            weight=litellm_params.get('weight', 1),
        )

        assert params.model == 'gpt-3.5-turbo'
        assert params.api_key == 'sk-test'
        assert params.base_url == ''  # 默认值
        assert params.provider == 'openai'  # 默认值
        assert params.max_tokens == 4096  # 默认值
        assert params.rpm == 60  # 默认值
        assert params.tpm == 100000  # 默认值
        assert params.weight == 1  # 默认值

    def test_empty_config(self):
        """测试空配置"""
        litellm_params = {}

        params = ModelEndPoint(
            model=litellm_params.get('model', ''),
            api_key=litellm_params.get('api_key', ''),
            base_url=litellm_params.get('base_url', ''),
            provider=litellm_params.get('provider', 'openai'),
            max_tokens=litellm_params.get('max_tokens', 4096),
            rpm=litellm_params.get('rpm', 60),
            tpm=litellm_params.get('tpm', 100000),
            weight=litellm_params.get('weight', 1),
        )

        assert params.model == ''
        assert params.api_key == ''
        assert params.base_url == ''
        assert params.provider == 'openai'
        assert params.max_tokens == 4096
        assert params.rpm == 60
        assert params.tpm == 100000
        assert params.weight == 1


class TestModelConfigConversion:
    """测试模型配置转换"""

    def test_yaml_to_model_config_single_node(self):
        """测试 YAML 到 ModelConfig 的转换（单节点模式）"""
        from config_manager import ConfigManager

        # 模拟数据库配置
        db_config = MagicMock()
        db_config.model_name = 'test-model'
        db_config.litellm_params = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'sk-test',
            'base_url': 'https://api.openai.com/v1',
            'provider': 'openai',
            'max_tokens': 4096,
            'rpm': 60,
            'tpm': 100000,
            'weight': 1
        }
        db_config.support_types = ['text']
        db_config.default_rpm = 10
        db_config.default_tpm = 100000
        db_config.default_max_tokens = 32768
        db_config.description = 'Test model'

        cm = ConfigManager()
        model_config = cm.yaml_to_model_config(db_config)

        assert model_config is not None
        assert model_config.model_name == 'test-model'
        assert isinstance(model_config.litellm_params, ModelEndPoint)
        assert model_config.litellm_params.model == 'gpt-3.5-turbo'
        assert model_config.litellm_params.provider == 'openai'

    def test_yaml_to_model_config_missing_fields(self):
        """测试 YAML 到 ModelConfig 的转换（缺少字段）"""
        from config_manager import ConfigManager

        # 模拟数据库配置（缺少多个字段）
        db_config = MagicMock()
        db_config.model_name = 'test-model-minimal'
        db_config.litellm_params = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'sk-test'
            # 缺少 base_url, provider, max_tokens, rpm, tpm, weight
        }
        db_config.support_types = ['text']
        db_config.default_rpm = 10
        db_config.default_tpm = 100000
        db_config.default_max_tokens = 32768
        db_config.description = 'Test model with minimal config'

        cm = ConfigManager()
        model_config = cm.yaml_to_model_config(db_config)

        assert model_config is not None
        assert model_config.model_name == 'test-model-minimal'
        assert isinstance(model_config.litellm_params, ModelEndPoint)
        # 验证默认值
        assert model_config.litellm_params.base_url == ''
        assert model_config.litellm_params.provider == 'openai'
        assert model_config.litellm_params.max_tokens == 4096
        assert model_config.litellm_params.rpm == 60
        assert model_config.litellm_params.tpm == 100000
        assert model_config.litellm_params.weight == 1

    def test_yaml_to_model_config_multi_node(self):
        """测试 YAML 到 ModelConfig 的转换（多节点模式）"""
        from config_manager import ConfigManager

        # 模拟数据库配置（多节点）- 添加必要的 provider 字段
        db_config = MagicMock()
        db_config.model_name = 'test-model-multi'
        db_config.litellm_params = {
            'endpoints': [
                {
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'sk-test-1',
                    'base_url': 'https://api.openai.com/v1',
                    'weight': 2,
                    'max_tokens': 4096,
                    'rpm': 60,
                    'tpm': 100000,
                    'provider': 'openai',  # 必填字段
                },
                {
                    'model': 'gpt-3.5-turbo',
                    'api_key': 'sk-test-2',
                    'base_url': 'https://api.openai.com/v1',
                    'weight': 1,
                    'max_tokens': 4096,
                    'rpm': 60,
                    'tpm': 100000,
                    'provider': 'openai',  # 必填字段
                }
            ]
        }
        db_config.support_types = ['text']
        db_config.default_rpm = 10
        db_config.default_tpm = 100000
        db_config.default_max_tokens = 32768
        db_config.description = 'Test model with multiple endpoints'

        cm = ConfigManager()
        model_config = cm.yaml_to_model_config(db_config)

        assert model_config is not None
        assert model_config.model_name == 'test-model-multi'
        assert isinstance(model_config.litellm_params, ModelInfoList)
        assert len(model_config.litellm_params.endpoints) == 2
        assert model_config.litellm_params.endpoints[0].weight == 2
        assert model_config.litellm_params.endpoints[1].weight == 1


class TestAsyncGetModelConfig:
    """测试 async_get_model_config 函数"""

    @pytest.mark.asyncio
    async def test_get_model_from_db_success(self):
        """测试从数据库成功获取模型配置"""
        from config_manager import async_get_model_config
        from sqlalchemy.ext.asyncio import AsyncSession

        # 模拟数据库会话
        db_session = AsyncMock(spec=AsyncSession)

        # 模拟数据库查询结果
        mock_db_config = MagicMock()
        mock_db_config.model_name = 'test-model'
        mock_db_config.litellm_params = {
            'model': 'gpt-3.5-turbo',
            'api_key': 'sk-test',
            'base_url': 'https://api.openai.com/v1',
            'provider': 'openai',
            'max_tokens': 4096,
            'rpm': 60,
            'tpm': 100000,
            'weight': 1
        }
        mock_db_config.support_types = ['text']
        mock_db_config.default_rpm = 10
        mock_db_config.default_tpm = 100000
        mock_db_config.default_max_tokens = 32768
        mock_db_config.description = 'Test model'
        mock_db_config.is_active = True

        # 设置 mock
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = mock_db_config
        db_session.execute.return_value = mock_result

        config = await async_get_model_config('test-model', db_session)

        assert config is not None
        assert config.model_name == 'test-model'
        assert isinstance(config.litellm_params, ModelEndPoint)

    @pytest.mark.asyncio
    async def test_get_model_from_db_missing_fields(self):
        """测试从数据库获取模型配置（缺少字段） - 验证 404 问题修复"""
        from config_manager import async_get_model_config
        from sqlalchemy.ext.asyncio import AsyncSession

        # 模拟数据库会话
        db_session = AsyncMock(spec=AsyncSession)

        # 模拟数据库配置（缺少字段，模拟前端保存时可能缺少的情况）
        mock_db_config = MagicMock()
        mock_db_config.model_name = 'qwen3-coder'
        mock_db_config.litellm_params = {
            'model': 'qwen3-coder',
            'api_key': 'sk-test-key',
            'base_url': 'http://localhost:11434',
            'provider': 'ollama'
            # 缺少 max_tokens, rpm, tpm, weight, dimensions
        }
        mock_db_config.support_types = ['text']
        mock_db_config.default_rpm = 10
        mock_db_config.default_tpm = 100000
        mock_db_config.default_max_tokens = 32768
        mock_db_config.description = 'Qwen3 Coder model'
        mock_db_config.is_active = True

        # 设置 mock
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = mock_db_config
        db_session.execute.return_value = mock_result

        # 这是 404 问题的核心测试 - 修复前会返回 None，修复后应该返回有效配置
        config = await async_get_model_config('qwen3-coder', db_session)

        # 修复前：这里会断言失败，因为 config 为 None 导致 404
        # 修复后：应该成功返回配置
        assert config is not None, "模型配置不应为 None，否则会导致 404 错误"
        assert config.model_name == 'qwen3-coder'
        assert isinstance(config.litellm_params, ModelEndPoint)
        # 验证默认值是否正确应用
        assert config.litellm_params.max_tokens == 4096
        assert config.litellm_params.rpm == 60
        assert config.litellm_params.tpm == 100000
        assert config.litellm_params.weight == 1

    @pytest.mark.asyncio
    async def test_get_model_from_db_not_found(self):
        """测试数据库中不存在模型"""
        from config_manager import async_get_model_config
        from sqlalchemy.ext.asyncio import AsyncSession

        # 模拟数据库会话
        db_session = AsyncMock(spec=AsyncSession)

        # 设置 mock 返回 None
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        db_session.execute.return_value = mock_result

        config = await async_get_model_config('nonexistent-model', db_session)

        # 数据库中不存在，应回退到 YAML
        # 如果 YAML 中也没有，则返回 None
        assert config is None

    @pytest.mark.asyncio
    async def test_get_model_from_db_error(self):
        """测试数据库查询出错"""
        from config_manager import async_get_model_config
        from sqlalchemy.ext.asyncio import AsyncSession

        # 模拟数据库会话
        db_session = AsyncMock(spec=AsyncSession)

        # 设置 mock 抛出异常
        db_session.execute.side_effect = Exception("Database connection error")

        # 不应该抛出异常，而是回退到 YAML
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = await async_get_model_config('test-model', db_session)

            # 应该记录警告
            assert len(w) == 1
            assert "Database query failed" in str(w[0].message)


class TestModelConfigValidation:
    """测试 ModelConfig 的验证逻辑"""

    def test_global_vs_node_limits_warning(self):
        """测试全局限流与节点限流比较的警告"""
        # 当全局 RPM 大于节点最小 RPM 时，应该发出警告
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            params = ModelEndPoint(
                model='gpt-3.5-turbo',
                api_key='sk-test',
                base_url='https://api.openai.com/v1',
                provider='openai',
                max_tokens=4096,
                rpm=5,  # 节点 RPM
                tpm=50000,  # 节点 TPM
                weight=1,
            )

            model_config = ModelConfig(
                model_name='test-model',
                litellm_params=params,
                support_types=['text'],
                default_rpm=10,  # 全局 RPM > 节点 RPM (5)，应该警告
                default_tpm=100000,
                default_max_tokens=32768,
                description='Test model'
            )

            # 应该产生警告（全局 rpm 和 max_tokens 都会产生警告）
            assert len(w) >= 1
            assert any("全局 rpm" in str(warning.message) for warning in w)

    def test_valid_model_config(self):
        """测试有效的模型配置"""
        params = ModelEndPoint(
            model='gpt-3.5-turbo',
            api_key='sk-test',
            base_url='https://api.openai.com/v1',
            provider='openai',
            max_tokens=4096,
            rpm=60,
            tpm=100000,
            weight=1,
        )

        model_config = ModelConfig(
            model_name='gpt-3.5-turbo',
            litellm_params=params,
            support_types=['text', 'image'],
            default_rpm=10,
            default_tpm=100000,
            default_max_tokens=32768,
            description='GPT-3.5 Turbo'
        )

        assert model_config.model_name == 'gpt-3.5-turbo'
        assert model_config.support_types == ['text', 'image']
        assert model_config.default_rpm == 10
        assert model_config.default_max_tokens == 32768


# 运行测试的入口
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
