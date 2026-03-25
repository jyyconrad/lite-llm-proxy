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

# 1. 生成 TAG（今天的日期）
TAG=$(date +%Y%m%d)
echo -e "${YELLOW}使用镜像 TAG: ${TAG}${NC}"

# 2. 复制环境配置文件
if [ -f ".env-local" ]; then
    echo -e "${YELLOW}复制.env-local 到.env...${NC}"
    cp .env-docker .env

    # 添加 TAG 信息到.env 文件
    echo -e "${YELLOW}添加 TAG 信息到.env 文件...${NC}"
    # 检查是否已存在 TAG 配置，存在则替换，不存在则追加
    if grep -q "^TAG=" .env; then
        sed -i.bak "s/^TAG=.*/TAG=${TAG}/" .env
        rm -f .env.bak
    else
        echo "TAG=${TAG}" >> .env
    fi
    echo -e "${GREEN}环境配置文件已更新${NC}"
else
    echo -e "${RED}错误：.env-local 文件不存在！${NC}"
    exit 1
fi

# 3. 读取 PORT 配置
PORT=$(grep "^PORT=" .env-local | cut -d'=' -f2)
PORT=${PORT:-8000}  # 默认值 8000
echo -e "${YELLOW}检测到 PORT 配置：${PORT}${NC}"

# 4. 构建前端代码
echo -e "${YELLOW}构建前端代码...${NC}"
cd frontend
npm install
# 根据 PORT 配置修改 API 地址
sed -i.bak "s|window\.__API_BASE__ = '.*'|window.__API_BASE__ = 'http://localhost:${PORT}'|" index.html
rm -f index.html.bak
npm run build
cd ..
echo -e "${GREEN}前端构建完成${NC}"

# 5. 停止现有服务
echo -e "${YELLOW}停止现有 Docker 服务...${NC}"
docker compose --profile full down --remove-orphans

# 6. 删除旧的镜像
OLD_IMAGE="llm-proxy-single:${TAG}"
if docker images | grep -q "llm-proxy-single.*${TAG}"; then
    echo -e "${YELLOW}删除旧镜像：${OLD_IMAGE}...${NC}"
    docker rmi -f "${OLD_IMAGE}"
fi

# 7. 构建新镜像
echo -e "${YELLOW}构建新镜像：${OLD_IMAGE}...${NC}"
docker build -t "${OLD_IMAGE}" .

# 8. 启动服务
echo -e "${YELLOW}启动完整服务（app + db + redis）...${NC}"
docker compose --profile full up -d

# 9. 显示服务状态
echo -e "${GREEN}=== 服务启动完成 ===${NC}"
echo -e "${YELLOW}服务状态:${NC}"
docker compose ps

echo -e ""
echo -e "${GREEN}访问地址:${NC}"
echo -e "API 网关：http://localhost:${PORT}"
echo -e "管理后台：http://localhost:${PORT}/app"
echo -e "健康检查：http://localhost:${PORT}/health"
echo -e ""
echo -e "${YELLOW}查看日志：docker compose logs -f app${NC}"
echo -e "${YELLOW}停止服务：docker compose --profile full down${NC}"
