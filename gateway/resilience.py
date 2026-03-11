"""
弹性机制模块

提供重试、熔断器、失败转移等功能。
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger("gateway.resilience")


class CircuitState(Enum):
    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态（探测恢复）


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5  # 连续失败次数达到此值时熔断
    success_threshold: int = 2  # 半开状态下连续成功次数达到此值时关闭
    timeout: float = 30.0  # 熔断超时时间（秒）
    half_open_max_calls: int = 3  # 半开状态下的最大探测调用数


class CircuitBreaker:
    """熔断器实现"""

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        # 检查是否需要从 OPEN 转到 HALF_OPEN
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.config.timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(f"CircuitBreaker '{self.name}' transitioned to HALF_OPEN")
        return self._state

    def record_success(self):
        """记录成功调用"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"CircuitBreaker '{self.name}' transitioned to CLOSED")
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self):
        """记录失败调用"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning(
                f"CircuitBreaker '{self.name}' transitioned to OPEN (half_open failure)"
            )
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"CircuitBreaker '{self.name}' transitioned to OPEN (failure threshold reached)"
                )

    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
        return False


# 全局熔断器字典
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """获取或创建熔断器"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


T = TypeVar("T")


async def with_retry_and_circuit_breaker(
    func: Callable[..., Any],
    circuit_breaker: CircuitBreaker,
    max_retries: int = 2,
    retry_delay: float = 0.5,
    *args,
    **kwargs,
) -> Any:
    """
    带重试和熔断的函数调用

    Args:
        func: 要调用的异步函数
        circuit_breaker: 熔断器实例
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        *args, **kwargs: 函数参数

    Returns:
        函数返回值

    Raises:
        Exception: 当熔断器打开或重试次数用尽时
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        # 检查熔断器
        if not circuit_breaker.can_execute():
            raise Exception(f"Circuit breaker '{circuit_breaker.name}' is OPEN")

        try:
            result = await func(*args, **kwargs)
            circuit_breaker.record_success()
            return result
        except Exception as e:
            circuit_breaker.record_failure()
            last_exception = e
            logger.warning(
                f"CircuitBreaker '{circuit_breaker.name}' attempt {attempt + 1}/{max_retries + 1} failed: {e}"
            )

            if attempt < max_retries:
                # 指数退避
                delay = retry_delay * (2**attempt)
                await asyncio.sleep(delay)

    raise last_exception


# 重试配置类
@dataclass
class RetryConfig:
    """重试配置"""

    max_retries: int = 2
    initial_delay: float = 0.5
    max_delay: float = 5.0
    exponential_base: float = 2.0
    retry_on_status_codes: list[int] = field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )


# 默认重试配置
default_retry_config = RetryConfig()


def calculate_retry_delay(
    attempt: int, config: RetryConfig = default_retry_config
) -> float:
    """计算重试延迟（指数退避）"""
    delay = config.initial_delay * (config.exponential_base**attempt)
    return min(delay, config.max_delay)


# 节点健康状态
@dataclass
class NodeHealth:
    """节点健康状态"""

    endpoint: str
    is_healthy: bool = True
    failure_count: int = 0
    last_failure_time: float = 0.0
    success_count: int = 0


class FailoverManager:
    """失败转移管理器"""

    def __init__(self):
        self._node_health: dict[str, NodeHealth] = {}

    def register_node(self, endpoint: str):
        """注册节点"""
        if endpoint not in self._node_health:
            self._node_health[endpoint] = NodeHealth(endpoint=endpoint)

    def record_success(self, endpoint: str):
        """记录节点成功"""
        if endpoint in self._node_health:
            health = self._node_health[endpoint]
            health.is_healthy = True
            health.failure_count = 0
            health.success_count += 1

    def record_failure(self, endpoint: str):
        """记录节点失败"""
        if endpoint in self._node_health:
            health = self._node_health[endpoint]
            health.failure_count += 1
            health.last_failure_time = time.time()
            if health.failure_count >= 3:
                health.is_healthy = False
                logger.warning(
                    f"Node {endpoint} marked as unhealthy (failures: {health.failure_count})"
                )

    def get_healthy_nodes(self, endpoints: list[str]) -> list[str]:
        """获取健康节点列表"""
        return [
            ep
            for ep in endpoints
            if ep in self._node_health and self._node_health[ep].is_healthy
        ]

    def is_node_healthy(self, endpoint: str) -> bool:
        """检查节点是否健康"""
        if endpoint not in self._node_health:
            return True
        return self._node_health[endpoint].is_healthy


# 全局失败转移管理器
_failover_manager = FailoverManager()


def get_failover_manager() -> FailoverManager:
    """获取失败转移管理器"""
    return _failover_manager
