# -*- coding: utf-8 -*-
"""
模型配置单元测试

测试范围:
1. ModelEndPoint 默认值处理
2. async_get_model_config 函数 (完整字段、部分字段缺失、空配置)
3. 模型配置转换流程 (YAML 到模型、数据库到模型)
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from data.model_info import ModelConfig, ModelEndPoint, ModelInfoList
from config_manager import ConfigManager, async_get_model_config


# --------------------------------------------------------------------------- #
# 测试 ModelEndPoint 默认值处理
# --------------------------------------------------------------------------- #
class TestModelEndPointDefaults:
    """测试 ModelEndPoint 的默认值处理"""

    def test_complete_fields(self):
        """测试完整字段配置"""
        params = ModelEndPoint(
            model="gpt-3.5-turbo",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            provider="openai",
            max_tokens=4096,
            rpm=60,
            tpm=100000,
            weight=1,
        )
        assert params.model == "gpt-3.5-turbo"
        assert params.api_key == "sk-test"
        assert params.base_url == "https://api.openai.com/v1"
        assert params.provider == "openai"
        assert params.max_tokens == 4096
        assert params.rpm == 60
        assert params.tpm == 100000
        assert params.weight == 1

    def test_missing_optional_fields(self):
        """测试缺少可选字段时使用默认值"""
        # 只提供必填字段，验证可选字段的默认值
        params = ModelEndPoint(
            model="gpt-3.5-turbo",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            provider="openai",
            max_tokens=4096,
            rpm=60,
            tpm=100000,
        )
        # weight 应该有默认值 1
        assert params.weight == 1
        # dimensions 应该有默认值 None
        assert params.dimensions is None

    def test_empty_config(self):
        """测试空配置 - 验证必填字段的验证逻辑"""
        # 必填字段缺失应该抛出验证错误
        with pytest.raises(Exception):  # pydantic 验证错误
            ModelEndPoint()

    def test_partial_missing_fields(self):
        """测试部分字段缺失"""
        # 只提供 model 和 api_key，其他字段使用默认值
        params = ModelEndPoint(
            model="gpt-3.5-turbo",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            provider="openai",
            max_tokens=4096,
            rpm=60,
            tpm=100000,
        )
        assert params.model == "gpt-3.5-turbo"
        assert params.weight == 1  # 默认值
        assert params.dimensions is None  # 默认值

    def test_zero_weight(self):
        """测试 weight=0 的情况"""
        params = ModelEndPoint(
            model="gpt-3.5-turbo",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            provider="openai",
            max_tokens=4096,
            rpm=60,
            tpm=100000,
            weight=0,
        )
        assert params.weight == 0

    def test_zero_rate_limits(self):
        """测试 rpm=0 和 tpm=0 的情况 (表示不限)"""
        params = ModelEndPoint(
            model="gpt-3.5-turbo",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            provider="openai",
            max_tokens=4096,
            rpm=0,
            tpm=0,
        )
        assert params.rpm == 0
        assert params.tpm == 0

    def test_dimensions_field(self):
        """测试 dimensions 字段"""
        params = ModelEndPoint(
            model="text-embedding-ada-002",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            provider="openai",
            max_tokens=4096,
            rpm=60,
            tpm=100000,
            dimensions=1536,
        )
        assert params.dimensions == 1536


# --------------------------------------------------------------------------- #
# 测试 async_get_model_config 函数
# --------------------------------------------------------------------------- #
class TestAsyncGetModelConfig:
    """测试 async_get_model_config 函数"""

    @pytest.fixture
    def mock_db_session(self):
        """创建 mock 数据库会话"""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_complete_database_config(self, mock_db_session):
        """测试正常情况：数据库中有完整配置"""
        # 准备数据库配置
        db_config = MagicMock()
        db_config.model_name = "test-model"
        db_config.litellm_params = {
            "model": "gpt-3.5-turbo",
            "api_key": "sk-test",
            "base_url": "https://api.openai.com/v1",
            "provider": "openai",
            "max_tokens": 4096,
            "rpm": 60,
            "tpm": 100000,
            "weight": 1,
        }
        db_config.support_types = ["text"]
        db_config.default_rpm = 10
        db_config.default_tpm = 100000
        db_config.default_max_tokens = 32768
        db_config.description = "Test model"

        # Mock 数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = db_config
        mock_db_session.execute.return_value = mock_result

        # 调用函数
        result = await async_get_model_config("test-model", mock_db_session)

        # 验证结果
        assert result is not None
        assert result.model_name == "test-model"
        assert isinstance(result.litellm_params, ModelEndPoint)
        assert result.litellm_params.model == "gpt-3.5-turbo"
        assert result.litellm_params.provider == "openai"

    @pytest.mark.asyncio
    async def test_database_config_missing_fields(self, mock_db_session):
        """测试边界情况：数据库配置缺少可选字段"""
        # 准备缺少字段的数据库配置
        db_config = MagicMock()
        db_config.model_name = "test-model"
        db_config.litellm_params = {
            "model": "gpt-3.5-turbo",
            "api_key": "sk-test",
            # 缺失 base_url, provider, max_tokens, rpm, tpm, weight
        }
        db_config.support_types = ["text"]
        db_config.default_rpm = 10
        db_config.default_tpm = 100000
        db_config.default_max_tokens = 32768
        db_config.description = "Test model"

        # Mock 数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = db_config
        mock_db_session.execute.return_value = mock_result

        # 调用函数 - 应该使用默认值而不是抛出异常
        result = await async_get_model_config("test-model", mock_db_session)

        # 验证结果 - 应该有默认值
        assert result is not None
        assert result.model_name == "test-model"
        assert isinstance(result.litellm_params, ModelEndPoint)
        assert result.litellm_params.model == "gpt-3.5-turbo"
        assert result.litellm_params.provider == "openai"  # 默认值
        assert result.litellm_params.max_tokens == 4096  # 默认值
        assert result.litellm_params.rpm == 60  # 默认值
        assert result.litellm_params.tpm == 100000  # 默认值
        assert result.litellm_params.weight == 1  # 默认值

    @pytest.mark.asyncio
    async def test_empty_database_config(self, mock_db_session):
        """测试边界情况：数据库配置为空"""
        # Mock 数据库查询返回 None
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Mock config_manager 返回 None (YAML 中也没有)
        with patch("config_manager.config_manager") as mock_config_manager:
            mock_config_manager.get_model_config.return_value = None
            mock_config_manager.refresh_if_needed.return_value = None

            # 调用函数
            result = await async_get_model_config("non-existent-model", mock_db_session)

            # 验证结果 - 应该返回 None
            assert result is None

    @pytest.mark.asyncio
    async def test_partial_fields_missing(self, mock_db_session):
        """测试边界情况：部分字段缺失"""
        # 准备部分字段缺失的数据库配置
        db_config = MagicMock()
        db_config.model_name = "test-model"
        db_config.litellm_params = {
            "model": "gpt-3.5-turbo",
            "api_key": "sk-test",
            "base_url": "https://api.openai.com/v1",
            # 缺失 provider, max_tokens, rpm, tpm, weight
        }
        db_config.support_types = ["text"]
        db_config.default_rpm = 10
        db_config.default_tpm = 100000
        db_config.default_max_tokens = 32768
        db_config.description = "Test model"

        # Mock 数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = db_config
        mock_db_session.execute.return_value = mock_result

        # 调用函数
        result = await async_get_model_config("test-model", mock_db_session)

        # 验证结果 - 缺失的字段应该有默认值
        assert result is not None
        assert result.litellm_params.provider == "openai"  # 默认值
        assert result.litellm_params.max_tokens == 4096  # 默认值
        assert result.litellm_params.rpm == 60  # 默认值
        assert result.litellm_params.tpm == 100000  # 默认值
        assert result.litellm_params.weight == 1  # 默认值

    @pytest.mark.asyncio
    async def test_fallback_to_yaml(self, mock_db_session):
        """测试回退到 YAML 配置"""
        # Mock 数据库查询返回 None
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        mock_db_session.execute.return_value = mock_result

        # 准备 YAML 配置
        yaml_config = ModelConfig(
            model_name="yaml-model",
            litellm_params=ModelEndPoint(
                model="gpt-4",
                api_key="sk-yaml",
                base_url="https://api.openai.com/v1",
                provider="openai",
                max_tokens=8192,
                rpm=100,
                tpm=200000,
                weight=1,
            ),
            support_types=["text"],
            default_rpm=10,
            default_tpm=100000,
            default_max_tokens=32768,
            description="YAML model",
        )

        # Mock config_manager 返回 YAML 配置
        with patch("config_manager.config_manager") as mock_config_manager:
            mock_config_manager.get_model_config.return_value = yaml_config
            mock_config_manager.refresh_if_needed.return_value = None

            # 调用函数
            result = await async_get_model_config("yaml-model", mock_db_session)

            # 验证结果 - 应该返回 YAML 配置
            assert result is not None
            assert result.model_name == "yaml-model"
            assert result.litellm_params.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_database_error_fallback_to_yaml(self, mock_db_session):
        """测试数据库查询错误时回退到 YAML"""
        # Mock 数据库查询抛出异常
        mock_db_session.execute.side_effect = Exception("Database connection error")

        # 准备 YAML 配置
        yaml_config = ModelConfig(
            model_name="yaml-model",
            litellm_params=ModelEndPoint(
                model="gpt-4",
                api_key="sk-yaml",
                base_url="https://api.openai.com/v1",
                provider="openai",
                max_tokens=8192,
                rpm=100,
                tpm=200000,
                weight=1,
            ),
            support_types=["text"],
            default_rpm=10,
            default_tpm=100000,
            default_max_tokens=32768,
            description="YAML model",
        )

        # Mock config_manager 返回 YAML 配置
        with patch("config_manager.config_manager") as mock_config_manager:
            mock_config_manager.get_model_config.return_value = yaml_config
            mock_config_manager.refresh_if_needed.return_value = None

            # 调用函数
            result = await async_get_model_config("yaml-model", mock_db_session)

            # 验证结果 - 应该返回 YAML 配置
            assert result is not None
            assert result.model_name == "yaml-model"


# --------------------------------------------------------------------------- #
# 测试模型配置转换流程
# --------------------------------------------------------------------------- #
class TestModelConfigConversion:
    """测试模型配置转换流程"""

    def test_yaml_to_model_config_complete(self):
        """测试 YAML 到模型的完整转换"""
        config_manager = ConfigManager.__new__(ConfigManager)

        # 创建 mock 数据库配置
        db_config = MagicMock()
        db_config.model_name = "test-model"
        db_config.litellm_params = {
            "model": "gpt-3.5-turbo",
            "api_key": "sk-test",
            "base_url": "https://api.openai.com/v1",
            "provider": "openai",
            "max_tokens": 4096,
            "rpm": 60,
            "tpm": 100000,
            "weight": 1,
        }
        db_config.support_types = ["text", "image"]
        db_config.default_rpm = 10
        db_config.default_tpm = 100000
        db_config.default_max_tokens = 32768
        db_config.description = "Test model"

        # 调用转换方法
        result = config_manager.yaml_to_model_config(db_config)

        # 验证结果
        assert result is not None
        assert result.model_name == "test-model"
        assert isinstance(result.litellm_params, ModelEndPoint)
        assert result.litellm_params.model == "gpt-3.5-turbo"
        assert result.support_types == ["text", "image"]
        assert result.default_rpm == 10
        assert result.default_tpm == 100000
        assert result.default_max_tokens == 32768

    def test_yaml_to_model_config_missing_fields(self):
        """测试 YAML 到模型转换时处理缺失字段"""
        config_manager = ConfigManager.__new__(ConfigManager)

        # 创建缺少字段的数据库配置
        db_config = MagicMock()
        db_config.model_name = "test-model"
        db_config.litellm_params = {
            "model": "gpt-3.5-turbo",
            "api_key": "sk-test",
            # 缺失其他字段
        }
        db_config.support_types = None
        db_config.default_rpm = 10
        db_config.default_tpm = 100000
        db_config.default_max_tokens = 32768
        db_config.description = "Test model"

        # 调用转换方法 - 应该使用默认值
        result = config_manager.yaml_to_model_config(db_config)

        # 验证结果 - 应该有默认值
        assert result is not None
        assert result.litellm_params.provider == "openai"  # 默认值
        assert result.litellm_params.max_tokens == 4096  # 默认值
        assert result.litellm_params.rpm == 60  # 默认值
        assert result.litellm_params.tpm == 100000  # 默认值
        assert result.litellm_params.weight == 1  # 默认值

    def test_yaml_to_model_config_multinode(self):
        """测试多节点模式转换"""
        config_manager = ConfigManager.__new__(ConfigManager)

        # 创建多节点数据库配置
        db_config = MagicMock()
        db_config.model_name = "test-model"
        db_config.litellm_params = {
            "endpoints": [
                {
                    "model": "gpt-3.5-turbo-1",
                    "api_key": "sk-test-1",
                    "base_url": "https://api1.openai.com/v1",
                    "provider": "openai",
                    "max_tokens": 4096,
                    "rpm": 60,
                    "tpm": 100000,
                    "weight": 2,
                },
                {
                    "model": "gpt-3.5-turbo-2",
                    "api_key": "sk-test-2",
                    "base_url": "https://api2.openai.com/v1",
                    "provider": "openai",
                    "max_tokens": 4096,
                    "rpm": 60,
                    "tpm": 100000,
                    "weight": 1,
                },
            ]
        }
        db_config.support_types = ["text"]
        db_config.default_rpm = 10
        db_config.default_tpm = 100000
        db_config.default_max_tokens = 32768
        db_config.description = "Test model"

        # 调用转换方法
        result = config_manager.yaml_to_model_config(db_config)

        # 验证结果 - 应该是多节点模式
        assert result is not None
        assert isinstance(result.litellm_params, ModelInfoList)
        assert len(result.litellm_params.endpoints) == 2
        assert result.litellm_params.endpoints[0].weight == 2
        assert result.litellm_params.endpoints[1].weight == 1

    def test_model_config_validation_warning(self):
        """测试 ModelConfig 验证器警告"""
        import warnings

        # 创建配置，其中全局 RPM 大于节点 RPM
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            model_config = ModelConfig(
                model_name="test-model",
                litellm_params=ModelEndPoint(
                    model="gpt-3.5-turbo",
                    api_key="sk-test",
                    base_url="https://api.openai.com/v1",
                    provider="openai",
                    max_tokens=4096,
                    rpm=10,  # 节点 RPM
                    tpm=100000,
                    weight=1,
                ),
                support_types=["text"],
                default_rpm=100,  # 全局 RPM > 节点 RPM
                default_tpm=100000,
                default_max_tokens=32768,
                description="Test model",
            )

            # 应该产生警告
            assert len(w) > 0
            assert any("rpm" in str(warning.message).lower() for warning in w)


# --------------------------------------------------------------------------- #
# 测试前端配置格式兼容性
# --------------------------------------------------------------------------- #
class TestFrontendConfigCompatibility:
    """测试前端配置格式的兼容性"""

    def test_frontend_single_node_format(self):
        """测试前端单节点格式"""
        # 模拟前端发送的配置
        frontend_config = {
            "model_name": "my-model",
            "litellm_params": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": "sk-xxx",
                "base_url": "https://api.openai.com/v1",
                "max_tokens": 4096,
                "rpm": 60,
                "tpm": 100000,
                "weight": 1,
            },
        }

        # 转换为 ModelConfig
        params = ModelEndPoint(
            model=frontend_config["litellm_params"].get("model", ""),
            api_key=frontend_config["litellm_params"].get("api_key", ""),
            base_url=frontend_config["litellm_params"].get("base_url", ""),
            provider=frontend_config["litellm_params"].get("provider", "openai"),
            max_tokens=frontend_config["litellm_params"].get("max_tokens", 4096),
            rpm=frontend_config["litellm_params"].get("rpm", 60),
            tpm=frontend_config["litellm_params"].get("tpm", 100000),
            weight=frontend_config["litellm_params"].get("weight", 1),
        )

        model_config = ModelConfig(
            model_name=frontend_config["model_name"],
            litellm_params=params,
            support_types=["text"],
            default_rpm=10,
            default_tpm=100000,
            default_max_tokens=32768,
            description="Frontend model",
        )

        # 验证
        assert model_config is not None
        assert model_config.model_name == "my-model"
        assert model_config.litellm_params.model == "gpt-3.5-turbo"
        assert model_config.litellm_params.provider == "openai"

    def test_frontend_config_missing_optional_fields(self):
        """测试前端配置缺少可选字段"""
        # 模拟前端发送的不完整配置
        frontend_config = {
            "model_name": "my-model",
            "litellm_params": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": "sk-xxx",
                # 缺失 base_url, max_tokens, rpm, tpm, weight
            },
        }

        # 使用 .get() 提供默认值
        params = ModelEndPoint(
            model=frontend_config["litellm_params"].get("model", ""),
            api_key=frontend_config["litellm_params"].get("api_key", ""),
            base_url=frontend_config["litellm_params"].get("base_url", ""),
            provider=frontend_config["litellm_params"].get("provider", "openai"),
            max_tokens=frontend_config["litellm_params"].get("max_tokens", 4096),
            rpm=frontend_config["litellm_params"].get("rpm", 60),
            tpm=frontend_config["litellm_params"].get("tpm", 100000),
            weight=frontend_config["litellm_params"].get("weight", 1),
        )

        # 验证 - 应该使用默认值
        assert params.model == "gpt-3.5-turbo"
        assert params.base_url == ""  # 默认值
        assert params.max_tokens == 4096  # 默认值
        assert params.rpm == 60  # 默认值
        assert params.tpm == 100000  # 默认值
        assert params.weight == 1  # 默认值


# --------------------------------------------------------------------------- #
# 测试 ConfigManager 类
# --------------------------------------------------------------------------- #
class TestConfigManager:
    """测试 ConfigManager 类"""

    def _create_mock_config_manager(self):
        """创建带有必要属性的 mock ConfigManager"""
        import threading
        config_manager = ConfigManager.__new__(ConfigManager)
        config_manager.models_config = {}
        config_manager.cache_lock = threading.Lock()
        config_manager.config_cache = {}
        config_manager.last_modified = 0
        config_manager.last_check_time = 0
        config_manager.config_path = "./litellm_config.yaml"
        return config_manager

    def test_convert_legacy_model_config_old_format(self):
        """测试旧格式模型配置转换"""
        config_manager = ConfigManager.__new__(ConfigManager)

        # 旧格式配置（包含 model_info）
        old_format = {
            "model_name": "gpt-4",
            "model_info": {
                "provider": "openai",
                "max_tokens": 8192,
            },
            "litellm_params": {
                "model": "gpt-4-turbo",
                "api_key": "sk-test",
            },
            "rpm": 100,
            "tpm": 200000,
        }

        result = config_manager._convert_legacy_model_config(old_format)

        assert result["model_name"] == "gpt-4"
        assert result["litellm_params"]["provider"] == "openai"
        assert result["litellm_params"]["max_tokens"] == 8192
        assert result["litellm_params"]["weight"] == 1
        assert result["litellm_params"]["rpm"] == 100
        assert result["litellm_params"]["tpm"] == 200000

    def test_convert_legacy_model_config_new_format(self):
        """测试新格式模型配置转换"""
        config_manager = ConfigManager.__new__(ConfigManager)

        # 新格式配置
        new_format = {
            "model_name": "gpt-4",
            "litellm_params": {
                "model": "gpt-4-turbo",
                "api_key": "sk-test",
            },
        }

        result = config_manager._convert_legacy_model_config(new_format)

        assert result["model_name"] == "gpt-4"
        assert result["support_types"] == ["text"]  # 默认值
        assert result["description"] == "模型 gpt-4"  # 默认值
        assert result["default_rpm"] == 10  # 默认值
        assert result["default_tpm"] == 100000  # 默认值
        assert result["default_max_tokens"] == 32 * 1024  # 默认值
        assert result["litellm_params"]["provider"] == "openai"  # 默认值
        assert result["litellm_params"]["weight"] == 1  # 默认值

    def test_convert_legacy_model_config_multinode(self):
        """测试多节点模式配置转换"""
        config_manager = ConfigManager.__new__(ConfigManager)

        # 多节点配置
        multinode_format = {
            "model_name": "gpt-4-loadbalance",
            "litellm_params": {
                "endpoints": [
                    {"model": "gpt-4-1", "api_key": "sk-1"},
                    {"model": "gpt-4-2", "api_key": "sk-2"},
                ]
            },
        }

        result = config_manager._convert_legacy_model_config(multinode_format)

        assert result["model_name"] == "gpt-4-loadbalance"
        assert "endpoints" in result["litellm_params"]
        assert len(result["litellm_params"]["endpoints"]) == 2
        assert result["litellm_params"]["endpoints"][0]["provider"] == "openai"
        assert result["litellm_params"]["endpoints"][0]["weight"] == 1

    def test_convert_legacy_model_config_support_types_string(self):
        """测试 support_types 为字符串时的转换"""
        config_manager = ConfigManager.__new__(ConfigManager)

        config = {
            "model_name": "embedding-model",
            "support_types": "embedding",  # 字符串而非列表
            "litellm_params": {
                "model": "text-embedding-ada-002",
                "api_key": "sk-test",
            },
        }

        result = config_manager._convert_legacy_model_config(config)

        assert result["support_types"] == ["embedding"]  # 转换为列表

    def test_get_all_models(self):
        """测试获取所有模型"""
        config_manager = self._create_mock_config_manager()
        config_manager.models_config = {
            "model-1": MagicMock(),
            "model-2": MagicMock(),
        }

        models = config_manager.get_all_models()

        assert "model-1" in models
        assert "model-2" in models
        assert len(models) == 2

    def test_get_model_config(self):
        """测试获取指定模型配置"""
        config_manager = self._create_mock_config_manager()
        mock_config = MagicMock()
        config_manager.models_config = {
            "target-model": mock_config,
        }

        result = config_manager.get_model_config("target-model")

        assert result == mock_config

    def test_get_model_config_not_found(self):
        """测试获取不存在的模型配置"""
        config_manager = self._create_mock_config_manager()
        config_manager.models_config = {
            "model-1": MagicMock(),
        }

        result = config_manager.get_model_config("non-existent")

        assert result is None

    def test_get_all_model_configs(self):
        """测试获取所有模型配置"""
        config_manager = self._create_mock_config_manager()
        mock_config1 = MagicMock()
        mock_config2 = MagicMock()
        config_manager.models_config = {
            "model-1": mock_config1,
            "model-2": mock_config2,
        }

        result = config_manager.get_all_model_configs()

        assert len(result) == 2
        assert result["model-1"] == mock_config1
        assert result["model-2"] == mock_config2

    def test_refresh_if_needed_no_modification(self):
        """测试文件未修改时不刷新"""
        import time
        config_manager = ConfigManager.__new__(ConfigManager)
        config_manager.CACHE_TTL = 60
        config_manager.last_check_time = time.time()
        config_manager.last_modified = time.time()

        # 不应该触发刷新
        config_manager.refresh_if_needed()

    @patch("os.path.getmtime")
    @patch("config_manager.ConfigManager.load_config")
    def test_refresh_if_needed_with_modification(self, mock_load, mock_getmtime):
        """测试文件修改时刷新"""
        import time
        config_manager = ConfigManager.__new__(ConfigManager)
        config_manager.CACHE_TTL = 60
        config_manager.last_check_time = 0
        config_manager.last_modified = 100
        config_manager.config_path = "./litellm_config.yaml"

        mock_getmtime.return_value = 200  # 文件已修改

        config_manager.refresh_if_needed()

        mock_load.assert_called_once()

    @patch("os.path.exists")
    def test_load_config_file_not_found(self, mock_exists):
        """测试配置文件不存在"""
        mock_exists.return_value = False
        config_manager = ConfigManager.__new__(ConfigManager)
        config_manager.config_path = "./non_existent.yaml"
        config_manager.last_modified = 0

        with pytest.raises(FileNotFoundError):
            config_manager.load_config()


# --------------------------------------------------------------------------- #
# 测试异步辅助函数
# --------------------------------------------------------------------------- #
class TestAsyncHelperFunctions:
    """测试异步辅助函数"""

    @pytest.mark.asyncio
    async def test_async_get_all_models_with_db(self):
        """测试异步获取所有模型"""
        from config_manager import async_get_all_models_with_db

        # Mock 数据库会话
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("model-1",), ("model-2",)]
        mock_session.execute.return_value = mock_result

        # Mock YAML 配置
        with patch("config_manager.config_manager") as mock_config_manager:
            mock_config_manager.get_all_models.return_value = ["yaml-model"]

            result = await async_get_all_models_with_db(mock_session)

            assert "model-1" in result
            assert "model-2" in result
            assert "yaml-model" in result

    @pytest.mark.asyncio
    async def test_async_get_all_models_with_db_error(self):
        """测试数据库错误时获取所有模型"""
        from config_manager import async_get_all_models_with_db

        # Mock 数据库会话抛出异常
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("DB error")

        # Mock YAML 配置
        with patch("config_manager.config_manager") as mock_config_manager:
            mock_config_manager.get_all_models.return_value = ["yaml-model"]

            result = await async_get_all_models_with_db(mock_session)

            assert "yaml-model" in result

    @pytest.mark.asyncio
    async def test_async_get_all_model_configs_with_db(self):
        """测试异步获取所有模型配置"""
        from config_manager import async_get_all_model_configs_with_db

        # Mock 数据库会话
        mock_session = AsyncMock()
        mock_db_config = MagicMock()
        mock_db_config.model_name = "db-model"
        mock_db_config.litellm_params = {
            "model": "gpt-4",
            "api_key": "sk-test",
            "base_url": "https://api.openai.com/v1",
            "provider": "openai",
            "max_tokens": 4096,
            "rpm": 60,
            "tpm": 100000,
            "weight": 1,
        }
        mock_db_config.support_types = ["text"]
        mock_db_config.default_rpm = 10
        mock_db_config.default_tpm = 100000
        mock_db_config.default_max_tokens = 32768
        mock_db_config.description = "DB model"

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = [mock_db_config]
        mock_session.execute.return_value = mock_result

        # Mock YAML 配置
        with patch("config_manager.config_manager") as mock_config_manager:
            mock_config_manager.get_all_model_configs.return_value = {}

            result = await async_get_all_model_configs_with_db(mock_session)

            assert "db-model" in result

    @pytest.mark.asyncio
    async def test_async_get_all_model_configs_with_db_error(self):
        """测试数据库错误时获取所有模型配置"""
        from config_manager import async_get_all_model_configs_with_db

        # Mock 数据库会话抛出异常
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("DB error")

        # Mock YAML 配置
        with patch("config_manager.config_manager") as mock_config_manager:
            mock_config_manager.get_all_model_configs.return_value = {}

            result = await async_get_all_model_configs_with_db(mock_session)

            assert len(result) == 0


# --------------------------------------------------------------------------- #
# 运行测试
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
