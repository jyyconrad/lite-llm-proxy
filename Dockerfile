# =======================
# Python运行阶段
# =======================
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
# RUN apt-get update && apt-get install -y \
#     gcc \
#     curl \
#     bash \
#     && rm -rf /var/lib/apt/lists/*

# 复制并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY main.py .
# COPY .env-docker ./.env
COPY config_manager.py .
# COPY litellm_config.yaml .
COPY gateway/ ./gateway/
COPY data/ ./data/
COPY scripts/ ./scripts/

# 从构建阶段复制前端构建产物
# COPY dist/ ./dist/
# 创建日志目录并设置权限
RUN mkdir -p logs
RUN mkdir -p dist

# 创建非root用户并修改目录权限
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    chown -R app:app /app/logs && \
    chmod 755 /app/logs

USER app

# 暴露端口
# EXPOSE PORT

# 复制启动脚本
# COPY start.sh .
# RUN chmod +x start.sh

# 启动应用
CMD ["python", "main.py"]