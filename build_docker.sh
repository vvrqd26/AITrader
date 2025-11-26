#!/bin/bash

set -e

echo "================================"
echo "  AI Trader Docker 镜像构建脚本"
echo "================================"
echo ""

IMAGE_NAME="ai-trader"
IMAGE_TAG="latest"
PLATFORM="linux/amd64"

echo "目标平台: $PLATFORM (Intel N100兼容)"
echo "镜像名称: $IMAGE_NAME:$IMAGE_TAG"
echo ""

if ! command -v docker &> /dev/null; then
    echo "错误: 未找到 Docker，请先安装 Docker"
    exit 1
fi

echo "检查 Docker 是否运行..."
if ! docker info &> /dev/null; then
    echo "错误: Docker 守护进程未运行"
    exit 1
fi

echo "清理旧镜像 (可选)..."
read -p "是否删除旧镜像? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker rmi $IMAGE_NAME:$IMAGE_TAG 2>/dev/null || true
    echo "旧镜像已删除"
fi

echo ""
echo "开始构建 Docker 镜像..."
echo "这可能需要几分钟时间..."
echo ""

docker build \
    --platform $PLATFORM \
    --tag $IMAGE_NAME:$IMAGE_TAG \
    --progress=plain \
    .

if [ $? -eq 0 ]; then
    echo ""
    echo "================================"
    echo "  镜像构建成功!"
    echo "================================"
    echo ""
    echo "镜像信息:"
    docker images | grep $IMAGE_NAME
    echo ""
    echo "镜像大小:"
    docker inspect $IMAGE_NAME:$IMAGE_TAG | grep Size
    echo ""
    
    echo "下一步操作:"
    echo ""
    echo "1. 导出镜像到文件 (用于NAS导入):"
    echo "   ./export_image.sh"
    echo ""
    echo "2. 或直接使用 docker-compose 启动:"
    echo "   docker-compose up -d"
    echo ""
    echo "3. 首次运行前，请编辑配置文件:"
    echo "   vim config/config.json"
    echo ""
else
    echo ""
    echo "================================"
    echo "  镜像构建失败!"
    echo "================================"
    exit 1
fi
