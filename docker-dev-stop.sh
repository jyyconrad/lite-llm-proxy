#!/bin/bash

# Docker Compose 开发环境停止脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}停止LiteLLM Proxy Docker开发环境...${NC}"

# 停止并删除容器
docker compose --profile full down "$@"

echo -e "${GREEN}服务已停止${NC}"

# 如果传递了-v参数，显示提示信息
if [[ "$*" == *"-v"* ]]; then
    echo -e "${YELLOW}注意：已删除所有数据卷，数据库和Redis数据已清空${NC}"
fi
