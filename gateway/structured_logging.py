"""
结构化日志模块

提供 JSON 格式的日志输出，便于日志分析和监控。
"""

import json
import logging
import datetime
import traceback
from typing import Any, Dict, Optional
import uuid


class JSONFormatter(logging.Formatter):
    """JSON 格式日志格式化器"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加线程和进程信息
        if hasattr(record, "thread"):
            log_data["thread_id"] = record.thread
        if hasattr(record, "process"):
            log_data["process_id"] = record.process

        # 添加 extra 字段
        if self.include_extra:
            extra = {
                k: v
                for k, v in record.__dict__.items()
                if k not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__
                and not k.startswith("_")
            }
            if extra:
                log_data["extra"] = extra

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handler()

    def _setup_handler(self):
        """设置日志处理器"""
        # 检查是否已有处理器
        if self.logger.handlers:
            return

        # 添加控制台处理器
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log(
        self, level: int, message: str, extra: Optional[Dict[str, Any]] = None, **kwargs
    ):
        """记录日志"""
        extra = extra or {}
        extra.update(kwargs)
        self.logger.log(level, message, extra=extra)

    def info(self, message: str, **kwargs):
        self.log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        self.log(logging.DEBUG, message, **kwargs)


# 全局结构化日志实例
def get_structured_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(name)


# 请求日志中间件辅助函数
def log_request(
    logger: logging.Logger,
    request_id: str,
    method: str,
    path: str,
    user_id: Optional[str] = None,
    **extra,
):
    """记录请求日志"""
    logger.info(
        f"{method} {path}",
        extra={
            "request_id": request_id,
            "user_id": user_id,
            "http_method": method,
            "http_path": path,
            "event": "request",
            **extra,
        },
    )


def log_response(
    logger: logging.Logger,
    request_id: str,
    status_code: int,
    duration_ms: float,
    **extra,
):
    """记录响应日志"""
    logger.info(
        f"Response {status_code}",
        extra={
            "request_id": request_id,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "event": "response",
            **extra,
        },
    )


def log_llm_request(
    logger: logging.Logger,
    request_id: str,
    model: str,
    user_id: str,
    tokens: int = 0,
    **extra,
):
    """记录 LLM 请求日志"""
    logger.info(
        f"LLM Request: {model}",
        extra={
            "request_id": request_id,
            "model": model,
            "user_id": user_id,
            "tokens": tokens,
            "event": "llm_request",
            **extra,
        },
    )


def log_llm_response(
    logger: logging.Logger,
    request_id: str,
    model: str,
    duration_ms: float,
    tokens: int = 0,
    cost: float = 0.0,
    **extra,
):
    """记录 LLM 响应日志"""
    logger.info(
        f"LLM Response: {model}",
        extra={
            "request_id": request_id,
            "model": model,
            "duration_ms": duration_ms,
            "tokens": tokens,
            "cost": cost,
            "event": "llm_response",
            **extra,
        },
    )
