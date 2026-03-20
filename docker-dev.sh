#!/bin/bash

# Docker Compose 开发环境启动脚本
# 功能：自动构建镜像、配置环境、启动服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== LiteLLM Proxy Docker 开发环境启动脚本 ===${NC}"

# 1. 生成TAG（今天的日期）
TAG=$(date +%Y%m%d)
echo -e "${YELLOW}使用镜像TAG: ${TAG}${NC}"

# 2. 复制环境配置文件
if [ -f ".env-local" ]; then
    echo -e "${YELLOW}复制.env-local到.env...${NC}"
    cp .env-docker .env

    # 添加TAG信息到.env文件
    echo -e "${YELLOW}添加TAG信息到.env文件...${NC}"
    # 检查是否已存在TAG配置，存在则替换，不存在则追加
    if grep -q "^TAG=" .env; then
        sed -i.bak "s/^TAG=.*/TAG=${TAG}/" .env
        rm -f .env.bak
    else
        echo "TAG=${TAG}" >> .env
    fi
    echo -e "${GREEN}环境配置文件已更新${NC}"
else
    echo -e "${RED}错误：.env-local文件不存在！${NC}"
    exit 1
fi

# 3. 停止现有服务
echo -e "${YELLOW}停止现有Docker服务...${NC}"
docker compose --profile full down --remove-orphans

# 4. 删除旧的镜像
OLD_IMAGE="llm-proxy-single:${TAG}"
if docker images | grep -q "llm-proxy-single.*${TAG}"; then
    echo -e "${YELLOW}删除旧镜像: ${OLD_IMAGE}...${NC}"
    docker rmi -f "${OLD_IMAGE}"
fi

# 5. 构建新镜像
echo -e "${YELLOW}构建新镜像: ${OLD_IMAGE}...${NC}"
docker build -t "${OLD_IMAGE}" .

# 6. 启动服务
echo -e "${YELLOW}启动完整服务（app + db + redis）...${NC}"
docker compose --profile full up -d

# 7. 显示服务状态
echo -e "${GREEN}=== 服务启动完成 ===${NC}"
echo -e "${YELLOW}服务状态:${NC}"
docker compose ps

echo -e ""
echo -e "${GREEN}访问地址:${NC}"
echo -e "API 网关: http://localhost:8000"
echo -e "管理后台: http://localhost:8000"
echo -e "健康检查: http://localhost:8000/health"
echo -e ""
echo -e "${YELLOW}查看日志: docker compose logs -f app${NC}"
echo -e "${YELLOW}停止服务: docker compose --profile full down${NC}"
