from sqlalchemy import Column, String, Integer, Boolean, DateTime, DECIMAL, Text, ForeignKey, JSON, UniqueConstraint, func
from sqlalchemy.orm import relationship
import uuid
from .db import Base

class User(Base):
    __tablename__ = "users"
    id           = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username     = Column(String(100), unique=True, nullable=False)
    email        = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # 密码哈希值
    role         = Column(String(50), default="user")
    budget_limit = Column(DECIMAL(10,2), default=1000)
    rpm_limit    = Column(Integer, default=60)
    tpm_limit    = Column(Integer, default=60000)
    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active    = Column(Boolean, default=True)

class APIKey(Base):
    __tablename__ = "api_keys"
    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key     = Column(String(255), unique=True, nullable=False)
    user_id     = Column(String(36))
    description = Column(Text)
    created_at  = Column(DateTime, server_default=func.now())
    is_active   = Column(Boolean, default=True)


class UsageStat(Base):
    __tablename__ = "usage_stats"
    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = Column(String(36))
    model_name    = Column(String(100), nullable=False)
    request_count = Column(Integer, default=0)
    total_tokens  = Column(Integer, default=0)
    total_cost    = Column(DECIMAL(10,6))
    created_at    = Column(DateTime, server_default=func.now())
    last_used     = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("user_id", "model_name", name="uq_user_model"),)


class CompletionLog(Base):
    __tablename__ = "completion_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    model_name = Column(String(100), nullable=False)
    request_data = Column(JSON, nullable=False)  # 存储请求的关键信息
    response_data = Column(JSON, nullable=True)  # 存储响应的关键信息
    request_tokens = Column(Integer, default=0)
    response_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(DECIMAL(10,6), default=0)
    status = Column(String(50), default="success")  # success, error
    error_message = Column(Text, nullable=True)
    duration = Column(Integer, default=0)  # 请求耗时（毫秒）
    created_at = Column(DateTime, server_default=func.now())


class CompletionDetail(Base):
    __tablename__ = "completion_details"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    completion_log_id = Column(String(36), ForeignKey("completion_logs.id"), nullable=False)
    messages = Column(JSON, nullable=True)  # 存储完整的对话消息
    tools = Column(JSON, nullable=True)  # 存储工具信息
    full_response = Column(JSON, nullable=True)  # 存储完整的模型响应
    created_at = Column(DateTime, server_default=func.now())

    # 关联到CompletionLog
    completion_log = relationship("CompletionLog", backref="details")


class ModelConfig(Base):
    """模型配置表，支持数据库化管理模型配置"""
    __tablename__ = "model_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name = Column(String(100), unique=True, nullable=False, index=True)
    litellm_params = Column(JSON, nullable=False)  # 存储 litellm 参数
    support_types = Column(JSON, default=["text"])  # 支持的类型 ["text", "image", "embedding"]
    default_rpm = Column(Integer, default=10)  # 默认 RPM 限制
    default_tpm = Column(Integer, default=100000)  # 默认 TPM 限制
    default_max_tokens = Column(Integer, default=32768)  # 默认最大 token 数
    description = Column(String(500), default="大语言模型")
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_pydantic(self) -> "ModelConfigPydantic":
        """转换为 Pydantic 模型用于 API 响应"""
        from data.model_info import ModelEndPoint, ModelInfoList
        from gateway.models import ModelConfigPydantic

        litellm_params = self.litellm_params
        params = None
        if isinstance(litellm_params, dict):
            if "endpoints" in litellm_params:
                params = ModelInfoList(**litellm_params)
            else:
                params = ModelEndPoint(**litellm_params)

        return ModelConfigPydantic(
            id=self.id,
            model_name=self.model_name,
            litellm_params=params,
            support_types=self.support_types or ["text"],
            default_rpm=self.default_rpm,
            default_tpm=self.default_tpm,
            default_max_tokens=self.default_max_tokens,
            description=self.description,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ConfigCheckpoint(Base):
    """配置同步检查点表，记录 YAML 与数据库配置的同步状态"""
    __tablename__ = "config_checkpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    config_type = Column(String(50), nullable=False, unique=True, default="litellm_config")  # 配置类型
    yaml_hash = Column(String(64), nullable=False)  # YAML 文件内容 SHA256 哈希
    db_hash = Column(String(64))  # 数据库配置 SHA256 哈希
    last_sync_source = Column(String(20))  # 最后同步来源："yaml" | "database" | "none"
    last_sync_time = Column(DateTime)  # 最后同步时间
    yaml_updated_at = Column(DateTime)  # YAML 文件修改时间戳
    db_updated_at = Column(DateTime)  # 数据库最后更新时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


