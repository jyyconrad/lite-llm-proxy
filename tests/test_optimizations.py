"""
全面测试验证脚本

测试所有新增的优化模块：
1. Redis 异步化
2. 限流 Pipeline
3. 熔断器
4. 配置缓存
5. 健康检查
"""

import asyncio
import sys
import os
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import AsyncMock, patch, MagicMock

# 测试配置
TEST_MODE = True  # 单元测试模式


def test_redis_async():
    """测试 T1.1: Redis 异步化"""
    print("\n" + "=" * 60)
    print("测试 T1.1: Redis 异步化")
    print("=" * 60)

    try:
        from gateway.dependencies import get_redis, parse_redis

        # 测试 Redis URL 解析
        test_cases = [
            ("redis://localhost:6379", ("localhost", 6379, None)),
            ("redis://:password@localhost:6379", ("localhost", 6379, "password")),
            ("redis://user:pass@redis.internal:6380", ("redis.internal", 6380, "pass")),
            ("redis://localhost", ("localhost", 6379, None)),
        ]

        for url, expected in test_cases:
            result = parse_redis(url)
            assert result == expected, f"Failed for {url}: {result} != {expected}"

        print("✓ Redis URL 解析测试通过")

        # 测试异步 get_redis 函数签名
        import inspect
        from gateway.dependencies import get_redis

        assert inspect.iscoroutinefunction(get_redis), "get_redis 应该是异步函数"
        print("✓ get_redis 是异步函数")

        print("\n✅ T1.1 测试通过: Redis 异步化正常工作")
        return True

    except Exception as e:
        print(f"\n❌ T1.1 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_pipeline_optimization():
    """测试 T1.2: Pipeline 优化"""
    print("\n" + "=" * 60)
    print("测试 T1.2: Pipeline 优化")
    print("=" * 60)

    try:
        # 检查 check_rate_limit 使用 Pipeline
        import inspect
        from gateway.dependencies import check_rate_limit

        source = inspect.getsource(check_rate_limit)
        assert "pipeline" in source.lower(), "check_rate_limit 应该使用 Pipeline"
        assert "mget" in source.lower() or "pipeline" in source.lower(), (
            "应该使用 mget 或 Pipeline"
        )

        print("✓ check_rate_limit 使用了 Pipeline 优化")

        # 检查 incr_rate_limit 使用 Pipeline
        from gateway.dependencies import incr_rate_limit

        source = inspect.getsource(incr_rate_limit)
        assert "pipeline" in source.lower(), "incr_rate_limit 应该使用 Pipeline"

        print("✓ incr_rate_limit 使用了 Pipeline 优化")

        print("\n✅ T1.2 测试通过: Pipeline 优化已实现")
        return True

    except Exception as e:
        print(f"\n❌ T1.2 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_circuit_breaker():
    """测试 T2.2: 熔断器"""
    print("\n" + "=" * 60)
    print("测试 T2.2: 熔断器")
    print("=" * 60)

    try:
        from gateway.resilience import (
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitState,
            get_circuit_breaker,
        )

        # 测试熔断器配置
        config = CircuitBreakerConfig(
            failure_threshold=3, success_threshold=2, timeout=1.0
        )
        assert config.failure_threshold == 3
        assert config.success_threshold == 2
        assert config.timeout == 1.0
        print("✓ 熔断器配置正确")

        # 测试熔断器状态转换
        cb = CircuitBreaker("test_model", config)

        # 初始状态应该是 CLOSED
        assert cb.state == CircuitState.CLOSED
        print("✓ 初始状态为 CLOSED")

        # 记录失败，达到阈值
        for i in range(3):
            cb.record_failure()

        # 应该是 OPEN 状态
        assert cb.state == CircuitState.OPEN
        print("✓ 连续失败后转为 OPEN 状态")

        # OPEN 状态下不能执行
        assert not cb.can_execute()
        print("✓ OPEN 状态下 can_execute() 返回 False")

        # 等待超时后应该进入 HALF_OPEN
        time.sleep(1.5)
        assert cb.state == CircuitState.HALF_OPEN
        print("✓ 超时后转为 HALF_OPEN 状态")

        # 测试成功恢复
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        print("✓ 连续成功后转为 CLOSED 状态")

        # 测试 get_circuit_breaker
        cb2 = get_circuit_breaker("test_model_2")
        assert cb2.name == "test_model_2"
        print("✓ get_circuit_breaker 正常工作")

        print("\n✅ T2.2 测试通过: 熔断器功能正常")
        return True

    except Exception as e:
        print(f"\n❌ T2.2 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_failover_manager():
    """测试 T2失败转移"""
    print("\n" + "=" * 60)
    print("测试 T2.3: 失败转移")
    print("=" * 60)

    try:
        from gateway.resilience import FailoverManager, get_failover_manager, NodeHealth

        # 测试 FailoverManager
        fm = FailoverManager()

        # 注册节点
        fm.register_node("endpoint1")
        fm.register_node("endpoint2")

        assert "endpoint1" in fm._node_health
        assert "endpoint2" in fm._node_health
        print("✓ 节点注册成功")

        # 初始所有节点应该是健康的
        assert fm.is_node_healthy("endpoint1")
        assert fm.is_node_healthy("endpoint2")
        print("✓ 初始节点状态健康")

        # 记录失败
        fm.record_failure("endpoint1")
        fm.record_failure("endpoint1")
        fm.record_failure("endpoint1")

        # 节点应该变为不健康
        assert not fm.is_node_healthy("endpoint1")
        print("✓ 失败后节点标记为不健康")

        # 测试获取健康节点
        fm.register_node("endpoint3")
        healthy = fm.get_healthy_nodes(["endpoint1", "endpoint2", "endpoint3"])
        assert "endpoint2" in healthy
        assert "endpoint3" in healthy
        assert "endpoint1" not in healthy
        print("✓ get_healthy_nodes 正确过滤不健康节点")

        # 测试全局单例 - 使用模块级别的单例
        from gateway.resilience import _failover_manager

        fm2 = get_failover_manager()
        assert fm2 is _failover_manager
        print("✓ get_failover_manager 返回模块级单例")

        print("\n✅ T2.3 测试通过: 失败转移功能正常")
        return True

    except Exception as e:
        print(f"\n❌ T2.3 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_retry_config():
    """测试 T2.1: 重试配置"""
    print("\n" + "=" * 60)
    print("测试 T2.1: 重试配置")
    print("=" * 60)

    try:
        from gateway.resilience import (
            RetryConfig,
            default_retry_config,
            calculate_retry_delay,
        )

        # 测试默认配置
        assert default_retry_config.max_retries == 2
        assert default_retry_config.initial_delay == 0.5
        assert default_retry_config.max_delay == 5.0
        print("✓ 默认重试配置正确")

        # 测试指数退避
        delay0 = calculate_retry_delay(0)
        delay1 = calculate_retry_delay(1)
        delay2 = calculate_retry_delay(2)

        assert delay0 == 0.5  # 0.5 * 2^0
        assert delay1 == 1.0  # 0.5 * 2^1
        assert delay2 == 2.0  # 0.5 * 2^2
        print("✓ 指数退避计算正确")

        # 测试最大延迟限制
        delay10 = calculate_retry_delay(10)
        assert delay10 == 5.0  # 超过 max_delay
        print("✓ 最大延迟限制生效")

        print("\n✅ T2.1 测试通过: 重试配置正常")
        return True

    except Exception as e:
        print(f"\n❌ T2.1 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_config_cache():
    """测试 T3.4: 配置缓存"""
    print("\n" + "=" * 60)
    print("测试 T3.4: 配置缓存")
    print("=" * 60)

    try:
        from config_manager import ConfigManager, config_manager

        # 测试缓存 TTL
        assert hasattr(ConfigManager, "CACHE_TTL")
        assert ConfigManager.CACHE_TTL == 60
        print(f"✓ 缓存 TTL = {ConfigManager.CACHE_TTL} 秒")

        # 测试 ConfigManager 有 refresh_if_needed 方法
        assert hasattr(config_manager, "refresh_if_needed")
        print("✓ refresh_if_needed 方法存在")

        # 测试 get_model_config 方法
        models = config_manager.get_all_models()
        assert len(models) > 0
        print(f"✓ 已加载 {len(models)} 个模型配置")

        # 测试获取单个模型配置
        model_name = models[0]
        config = config_manager.get_model_config(model_name)
        assert config is not None
        print(f"✓ 模型 {model_name} 配置加载成功")

        print("\n✅ T3.4 测试通过: 配置缓存正常")
        return True

    except Exception as e:
        print(f"\n❌ T3.4 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_log_buffer():
    """测试 T1.3: 日志缓冲队列"""
    print("\n" + "=" * 60)
    print("测试 T1.3: 日志缓冲队列")
    print("=" * 60)

    try:
        from gateway.log_buffer import (
            LogBuffer,
            CompletionLogBuffer,
            get_completion_log_buffer,
        )

        # 测试日志缓冲初始化
        buffer = LogBuffer(flush_interval=0.1, batch_size=10)
        assert buffer.flush_interval == 0.1
        assert buffer.batch_size == 10
        print("✓ LogBuffer 参数正确")

        # 测试 CompletionLogBuffer
        cb = CompletionLogBuffer()
        assert isinstance(cb, LogBuffer)
        print("✓ CompletionLogBuffer 继承正确")

        # 测试全局单例
        buffer1 = get_completion_log_buffer()
        buffer2 = get_completion_log_buffer()
        assert buffer1 is buffer2
        print("✓ get_completion_log_buffer 返回单例")

        print("\n✅ T1.3 测试通过: 日志缓冲队列正常")
        return True

    except Exception as e:
        print(f"\n❌ T1.3 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_structured_logging():
    """测试 T4.1: 结构化日志"""
    print("\n" + "=" * 60)
    print("测试 T4.1: 结构化日志")
    print("=" * 60)

    try:
        from gateway.structured_logging import (
            JSONFormatter,
            StructuredLogger,
            get_structured_logger,
            log_request,
            log_response,
        )
        import logging

        # 测试 JSONFormatter
        formatter = JSONFormatter()
        assert isinstance(formatter, logging.Formatter)
        print("✓ JSONFormatter 继承正确")

        # 测试 StructuredLogger
        logger = get_structured_logger("test")
        assert isinstance(logger, StructuredLogger)
        print("✓ StructuredLogger 创建成功")

        # 测试日志方法存在
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
        print("✓ 日志方法完整")

        print("\n✅ T4.1 测试通过: 结构化日志正常")
        return True

    except Exception as e:
        print(f"\n❌ T4.1 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_metrics():
    """测试 T4.2: Prometheus 指标"""
    print("\n" + "=" * 60)
    print("测试 T4.2: Prometheus 指标")
    print("=" * 60)

    try:
        from gateway.metrics import (
            http_requests_total,
            http_request_duration_seconds,
            llm_requests_total,
            llm_tokens_total,
            llm_cost_total,
            llm_request_duration_seconds,
            circuit_breaker_state,
            rate_limit_hits_total,
            Metrics,
            metrics,
        )

        # 测试指标存在
        assert http_requests_total is not None
        assert llm_requests_total is not None
        print("✓ 指标定义存在")

        # 测试 Metrics 类
        assert hasattr(Metrics, "record_http_request")
        assert hasattr(Metrics, "record_llm_request")
        assert hasattr(Metrics, "record_llm_tokens")
        assert hasattr(Metrics, "record_llm_cost")
        print("✓ Metrics 辅助类方法完整")

        # 测试全局单例
        assert metrics is not None
        print("✓ 全局 metrics 实例存在")

        print("\n✅ T4.2 测试通过: Prometheus 指标正常")
        return True

    except Exception as e:
        print(f"\n❌ T4.2 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_gunicorn_config():
    """测试 T3.1: Gunicorn 配置"""
    print("\n" + "=" * 60)
    print("测试 T3.1: Gunicorn 配置")
    print("=" * 60)

    try:
        import gunicorn_config

        # 检查关键配置
        assert hasattr(gunicorn_config, "bind")
        assert hasattr(gunicorn_config, "workers")
        assert hasattr(gunicorn_config, "worker_class")
        assert hasattr(gunicorn_config, "timeout")

        print(f"✓ bind = {gunicorn_config.bind}")
        print(f"✓ workers = {gunicorn_config.workers}")
        print(f"✓ worker_class = {gunicorn_config.worker_class}")
        print(f"✓ timeout = {gunicorn_config.timeout}")

        print("\n✅ T3.1 测试通过: Gunicorn 配置正常")
        return True

    except Exception as e:
        print(f"\n❌ T3.1 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_db_pool_config():
    """测试 T3.3: 数据库连接池配置"""
    print("\n" + "=" * 60)
    print("测试 T3.3: 数据库连接池配置")
    print("=" * 60)

    try:
        from data.db import _get_optimal_pool_size

        # 测试动态池大小计算
        pool_size = _get_optimal_pool_size()
        assert pool_size > 0
        print(f"✓ 动态池大小 = {pool_size}")

        # 检查 _ensure_engine 函数存在
        from data.db import _ensure_engine
        import inspect

        assert inspect.isfunction(_ensure_engine)
        print("✓ _ensure_engine 函数存在")

        print("\n✅ T3.3 测试通过: 数据库连接池配置正常")
        return True

    except Exception as e:
        print(f"\n❌ T3.3 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_lua_script():
    """测试 T3.2: Lua 脚本"""
    print("\n" + "=" * 60)
    print("测试 T3.2: Lua 脚本")
    print("=" * 60)

    try:
        from gateway.dependencies import SLIDING_WINDOW_LUA_SCRIPT

        # 检查 Lua 脚本存在
        assert SLIDING_WINDOW_LUA_SCRIPT is not None
        assert len(SLIDING_WINDOW_LUA_SCRIPT) > 0
        print(f"✓ Lua 脚本长度 = {len(SLIDING_WINDOW_LUA_SCRIPT)} 字符")

        # 检查脚本包含关键指令
        assert "redis.call" in SLIDING_WINDOW_LUA_SCRIPT
        assert "INCR" in SLIDING_WINDOW_LUA_SCRIPT
        assert "EXPIRE" in SLIDING_WINDOW_LUA_SCRIPT
        print("✓ Lua 脚本包含必要的 Redis 命令")

        print("\n✅ T3.2 测试通过: Lua 脚本正常")
        return True

    except Exception as e:
        print(f"\n❌ T3.2 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_async_functions():
    """测试异步函数"""
    print("\n" + "=" * 60)
    print("测试异步函数")
    print("=" * 60)

    try:
        # 检查关键异步函数
        import inspect
        from gateway.dependencies import get_redis, check_rate_limit, incr_rate_limit
        from gateway.resilience import with_retry_and_circuit_breaker

        assert inspect.iscoroutinefunction(get_redis)
        assert inspect.iscoroutinefunction(check_rate_limit)
        assert inspect.iscoroutinefunction(incr_rate_limit)
        print("✓ 所有依赖函数都是异步的")

        print("\n✅ 异步函数测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 异步函数测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print(" " * 20 + "全面测试验证")
    print("=" * 70)

    results = {}

    # 同步测试
    results["T1.1 Redis 异步化"] = test_redis_async()
    results["T1.2 Pipeline 优化"] = test_pipeline_optimization()
    results["T1.3 日志缓冲队列"] = test_log_buffer()
    results["T2.1 重试配置"] = test_retry_config()
    results["T2.2 熔断器"] = test_circuit_breaker()
    results["T2.3 失败转移"] = test_failover_manager()
    results["T3.1 Gunicorn 配置"] = test_gunicorn_config()
    results["T3.2 Lua 脚本"] = test_lua_script()
    results["T3.3 数据库连接池"] = test_db_pool_config()
    results["T3.4 配置缓存"] = test_config_cache()
    results["T4.1 结构化日志"] = test_structured_logging()
    results["T4.2 Prometheus 指标"] = test_metrics()

    # 异步测试
    results["异步函数"] = asyncio.run(test_async_functions())

    # 汇总结果
    print("\n" + "=" * 70)
    print(" " * 25 + "测试结果汇总")
    print("=" * 70)

    passed = 0
    failed = 0

    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("=" * 70)
    print(f"总计: {passed} 通过, {failed} 失败")
    print("=" * 70)

    if failed > 0:
        print("\n⚠️  有测试失败，请检查上述错误")
        sys.exit(1)
    else:
        print("\n🎉 所有测试通过!")
        sys.exit(0)


if __name__ == "__main__":
    main()
