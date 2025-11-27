#!/bin/bash

set -e

echo "================================"
echo "  AI Trader 远程部署脚本"
echo "================================"
echo ""

# 默认配置
DEFAULT_REPO_URL="https://github.com/your-repo/ai-trader.git"
DEFAULT_BRANCH="main"

# 获取用户输入
read -p "请输入Git仓库URL (默认: $DEFAULT_REPO_URL): " REPO_URL
REPO_URL=${REPO_URL:-$DEFAULT_REPO_URL}

read -p "请输入分支名称 (默认: $DEFAULT_BRANCH): " BRANCH
BRANCH=${BRANCH:-$DEFAULT_BRANCH}

echo ""
echo "配置信息:"
echo "  仓库URL: $REPO_URL"
echo "  分支: $BRANCH"
echo ""

# 创建必要的目录
echo "创建配置目录..."
mkdir -p config logs data

# 检查Docker和docker-compose
if ! command -v docker &> /dev/null; then
    echo "错误: 未找到 Docker，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: 未找到 docker-compose，请先安装 docker-compose"
    exit 1
fi

echo "检查 Docker 是否运行..."
if ! docker info &> /dev/null; then
    echo "错误: Docker 守护进程未运行"
    exit 1
fi

# 设置环境变量
export REPO_URL=$REPO_URL
export BRANCH=$BRANCH

# 使用远程部署配置启动服务
echo "开始构建并启动服务..."
docker-compose -f docker-compose.remote.yml up -d --build

echo ""
echo "================================"
echo "  部署完成!"
echo "================================"
echo ""
echo "服务状态:"
docker-compose -f docker-compose.remote.yml ps
echo ""
echo "查看日志:"
echo "  docker-compose -f docker-compose.remote.yml logs -f"
echo ""
echo "访问Web面板:"
echo "  http://localhost:8000"
echo ""
echo "首次运行前，请编辑配置文件:"
echo "  vim config/config.json"
echo ""