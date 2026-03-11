"""Gunicorn 配置文件

用于生产环境多 Worker 部署
"""

import multiprocessing
import os

# 服务器 socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker 进程数
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5

# 日志
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "lite-llm-proxy"

# 服务器机制
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# 预加载应用代码（共享内存）
preload_app = True


# 钩子函数
def on_starting(server):
    """服务器启动时调用"""
    pass


def on_reload(server):
    """服务器重载时调用"""
    pass


def when_ready(server):
    """服务器准备好接受连接时调用"""
    pass


def pre_fork(server, worker):
    """fork worker 进程前调用"""
    pass


def post_fork(server, worker):
    """fork worker 进程后调用"""
    pass


def post_worker_init(worker):
    """worker 进程初始化完成后调用"""
    pass


def worker_int(worker):
    """worker 进程收到 SIGINT 或 SIGQUIT 时调用"""
    pass


def worker_abort(worker):
    """worker 进程收到 SIGABRT 时调用"""
    pass


def pre_exec(server):
    """重新执行 master 进程前调用"""
    pass


def pre_request(worker, req):
    """处理请求前调用"""
    worker.log.debug("%s %s" % (req.method, req.path))


def post_request(worker, req, environ, resp):
    """处理请求后调用"""
    pass


def child_exit(server, worker):
    """worker 进程退出时调用（master 进程）"""
    pass


def worker_exit(server, worker):
    """worker 进程退出时调用（worker 进程）"""
    pass


def nworkers_changed(server, new_value, old_value):
    """worker 数量变化时调用"""
    pass


def on_exit(server):
    """服务器退出时调用"""
    pass
