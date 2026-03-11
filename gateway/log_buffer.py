"""
日志缓冲队列模块

用于异步批量写入日志到数据库，减少数据库 I/O 压力。
"""

import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger("gateway.log_buffer")


class LogBuffer:
    """异步日志缓冲队列"""

    def __init__(
        self,
        flush_interval: float = 0.1,
        batch_size: int = 50,
        max_queue_size: int = 10000,
    ):
        """
        初始化日志缓冲队列

        Args:
            flush_interval: 刷新间隔（秒），默认 100ms
            batch_size: 批量大小，默认 50 条
            max_queue_size: 最大队列大小，默认 10000 条
        """
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size

        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动缓冲队列"""
        if self._running:
            return
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(
            f"LogBuffer started: flush_interval={self.flush_interval}s, batch_size={self.batch_size}"
        )

    async def stop(self):
        """停止缓冲队列并刷新剩余日志"""
        if not self._running:
            return
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # 刷新剩余的日志
        await self._flush()
        logger.info("LogBuffer stopped")

    async def put(self, log_entry: dict):
        """
        添加日志条目到缓冲队列

        Args:
            log_entry: 日志条目字典
        """
        try:
            self._queue.put_nowait(log_entry)
        except asyncio.QueueFull:
            # 队列已满，记录警告并丢弃最旧的日志
            logger.warning(f"Log buffer full, dropping oldest entry")
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                pass

    async def _flush_loop(self):
        """定期刷新日志的循环"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")

    async def _flush(self):
        """刷新缓冲队列中的日志到数据库"""
        if self._queue.empty():
            return

        batch = []
        try:
            # 尝试获取一批日志
            while len(batch) < self.batch_size and not self._queue.empty():
                batch.append(self._queue.get_nowait())
        except asyncio.QueueEmpty:
            pass

        if not batch:
            return

        try:
            await self._write_batch(batch)
            logger.debug(f"Flushed {len(batch)} log entries to database")
        except Exception as e:
            logger.error(f"Failed to write batch: {e}")
            # 将失败的日志放回队列（最多放回一条，避免无限循环）
            if batch:
                for entry in batch[:-1]:
                    try:
                        self._queue.put_nowait(entry)
                    except asyncio.QueueFull:
                        break

    async def _write_batch(self, batch: list[dict]):
        """
        写入一批日志到数据库

        Args:
            batch: 日志条目列表
        """
        # 这个方法需要由子类实现，或者通过回调函数注入
        pass


class CompletionLogBuffer(LogBuffer):
    """Completion Log 的专用缓冲队列"""

    def __init__(
        self,
        flush_interval: float = 0.1,
        batch_size: int = 50,
        max_queue_size: int = 10000,
        write_callback: Optional[Callable[[list[dict]], Any]] = None,
    ):
        super().__init__(flush_interval, batch_size, max_queue_size)
        self._write_callback = write_callback

    def set_write_callback(self, callback: Callable[[list[dict]], Any]):
        """设置写入回调函数"""
        self._write_callback = callback

    async def _write_batch(self, batch: list[dict]):
        """使用回调函数写入批次"""
        if self._write_callback:
            self._write_callback(batch)


# 全局日志缓冲实例
_completion_log_buffer: Optional[CompletionLogBuffer] = None


def get_completion_log_buffer() -> CompletionLogBuffer:
    """获取全局 CompletionLog 缓冲队列实例"""
    global _completion_log_buffer
    if _completion_log_buffer is None:
        _completion_log_buffer = CompletionLogBuffer(
            flush_interval=0.1,
            batch_size=50,
            max_queue_size=10000,
        )
    return _completion_log_buffer


async def init_log_buffer():
    """初始化日志缓冲队列"""
    buffer = get_completion_log_buffer()
    await buffer.start()
    return buffer


async def close_log_buffer():
    """关闭日志缓冲队列"""
    global _completion_log_buffer
    if _completion_log_buffer:
        await _completion_log_buffer.stop()
        _completion_log_buffer = None
