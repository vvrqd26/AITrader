#!/bin/bash

set -e

IMAGE_NAME="ai-trader"
IMAGE_TAG="latest"
OUTPUT_FILE="ai-trader-image.tar"

echo "================================"
echo "  导出 Docker 镜像"
echo "================================"
echo ""

if ! docker image inspect $IMAGE_NAME:$IMAGE_TAG &> /dev/null; then
    echo "错误: 镜像 $IMAGE_NAME:$IMAGE_TAG 不存在"
    echo "请先运行: ./build_docker.sh"
    exit 1
fi

echo "正在导出镜像到: $OUTPUT_FILE"
echo "这可能需要几分钟..."
echo ""

docker save -o $OUTPUT_FILE $IMAGE_NAME:$IMAGE_TAG

if [ $? -eq 0 ]; then
    FILE_SIZE=$(ls -lh $OUTPUT_FILE | awk '{print $5}')
    echo ""
    echo "================================"
    echo "  导出成功!"
    echo "================================"
    echo ""
    echo "文件: $OUTPUT_FILE"
    echo "大小: $FILE_SIZE"
    echo ""
    echo "传输到NAS后的使用方法:"
    echo ""
    echo "1. 上传 $OUTPUT_FILE 到NAS"
    echo ""
    echo "2. 在NAS上导入镜像:"
    echo "   docker load -i $OUTPUT_FILE"
    echo ""
    echo "3. 上传整个项目目录到NAS"
    echo ""
    echo "4. 在NAS上启动容器:"
    echo "   cd /path/to/ai-trader"
    echo "   docker-compose up -d"
    echo ""
    echo "5. 查看日志:"
    echo "   docker-compose logs -f"
    echo ""
    echo "6. 访问Web界面:"
    echo "   http://NAS-IP:8000"
    echo ""
else
    echo "导出失败!"
    exit 1
fi
