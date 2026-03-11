"""
Prometheus 指标模块

提供系统指标监控。
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import APIRouter, Response
import time

# 请求计数器
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

# 请求延迟直方图
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# LLM 请求计数器
llm_requests_total = Counter(
    "llm_requests_total", "Total LLM requests", ["model", "status"]
)

# LLM token 使用量
llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["model", "type"],  # type: prompt, completion, total
)

# LLM 请求成本
llm_cost_total = Counter("llm_cost_total", "Total LLM request cost", ["model"])

# LLM 请求延迟
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency in seconds",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0],
)

# 活跃连接数
active_connections = Gauge("active_connections", "Number of active connections")

# Redis 连接池状态
redis_pool_connections = Gauge(
    "redis_pool_connections",
    "Redis connection pool status",
    ["state"],  # state: idle, active
)

# 数据库连接池状态
db_pool_connections = Gauge(
    "db_pool_connections",
    "Database connection pool status",
    ["state"],  # state: idle, active, overflow
)

# 熔断器状态
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state",
    ["model", "state"],  # state: closed, open, half_open
)

# 限流计数器
rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits",
    ["user_id", "limit_type"],  # limit_type: rpm, tpm
)

# API 路由器
router = APIRouter()


@router.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


class Metrics:
    """指标记录辅助类"""

    @staticmethod
    def record_http_request(method: str, endpoint: str, status: int, duration: float):
        """记录 HTTP 请求"""
        http_requests_total.labels(
            method=method, endpoint=endpoint, status=status
        ).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )

    @staticmethod
    def record_llm_request(model: str, status: str, duration: float):
        """记录 LLM 请求"""
        llm_requests_total.labels(model=model, status=status).inc()
        llm_request_duration_seconds.labels(model=model).observe(duration)

    @staticmethod
    def record_llm_tokens(model: str, prompt_tokens: int, completion_tokens: int):
        """记录 LLM token 使用量"""
        llm_tokens_total.labels(model=model, type="prompt").inc(prompt_tokens)
        llm_tokens_total.labels(model=model, type="completion").inc(completion_tokens)
        llm_tokens_total.labels(model=model, type="total").inc(
            prompt_tokens + completion_tokens
        )

    @staticmethod
    def record_llm_cost(model: str, cost: float):
        """记录 LLM 请求成本"""
        llm_cost_total.labels(model=model).inc(cost)

    @staticmethod
    def record_rate_limit(user_id: str, limit_type: str):
        """记录限流命中"""
        rate_limit_hits_total.labels(user_id=user_id, limit_type=limit_type).inc()

    @staticmethod
    def set_circuit_breaker_state(model: str, state: str):
        """设置熔断器状态"""
        state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state, 0)
        circuit_breaker_state.labels(model=model, state=state).set(state_value)


# 全局指标实例
metrics = Metrics()
