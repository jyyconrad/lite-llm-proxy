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


