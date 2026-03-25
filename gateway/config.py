from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from functools import lru_cache
from typing import List, Optional

class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url:    str = Field(..., env="REDIS_URL")
    master_key:   str = Field(..., env="MASTER_KEY")
    admin_password:   str = Field(..., env="ADMIN_PASSWORD")
    litellm_config_path: str = "./litellm_config.yaml"
    
    # 新增字段以匹配环境变量
    http_proxy: Optional[str] = Field(None, env="HTTP_PROXY")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/app.log", env="LOG_FILE")
    log_max_bytes: int = Field(10485760, env="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(5, env="LOG_BACKUP_COUNT")
    default_rpm_limit: int = Field(60, env="DEFAULT_RPM_LIMIT")
    default_tpm_limit: int = Field(60000, env="DEFAULT_TPM_LIMIT")
    default_budget_limit: float = Field(1000.0, env="DEFAULT_BUDGET_LIMIT")
    jwt_secret: str = Field("your-jwt-secret-key-here", env="JWT_SECRET")
    cors_origins: List[str] = Field(["http://localhost:3000", "http://localhost:8080"], env="CORS_ORIGINS")
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    health_check_interval: int = Field(30, env="HEALTH_CHECK_INTERVAL")

    # LLM Request Timeout Configuration (in seconds)
    # Default: 300 seconds (5 minutes)
    request_timeout: int = Field(300, env="REQUEST_TIMEOUT")

    model_config = ConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()