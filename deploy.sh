#!/bin/bash

echo "================================"
echo "  AI Trader 一键部署脚本"
echo "  适用于绿联NAS (Intel N100)"
echo "================================"
echo ""

read -p "请选择部署方式:
1) 本地构建镜像并导出 (推荐)
2) 仅导出现有镜像
3) 使用docker-compose直接启动
请输入选项 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "开始构建镜像..."
        ./build_docker.sh
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "开始导出镜像..."
            ./export_image.sh
            
            echo ""
            echo "================================"
            echo "  完成! 请执行以下步骤:"
            echo "================================"
            echo ""
            echo "1. 上传文件到NAS:"
            echo "   - ai-trader-image.tar"
            echo "   - docker-compose.yml"
            echo "   - config/ 目录"
            echo ""
            echo "2. 在NAS上导入镜像:"
            echo "   docker load -i ai-trader-image.tar"
            echo ""
            echo "3. 编辑配置文件:"
            echo "   vim config/config.json"
            echo ""
            echo "4. 启动容器:"
            echo "   docker-compose up -d"
            echo ""
            echo "5. 访问Web界面:"
            echo "   http://NAS-IP:8000"
            echo ""
        fi
        ;;
    
    2)
        echo ""
        ./export_image.sh
        ;;
    
    3)
        echo ""
        echo "检查配置文件..."
        if [ ! -f "config/config.json" ]; then
            echo "警告: config/config.json 不存在"
            echo "请先创建配置文件"
            exit 1
        fi
        
        echo "启动容器..."
        docker-compose up -d
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "================================"
            echo "  容器已启动!"
            echo "================================"
            echo ""
            echo "查看日志: docker-compose logs -f"
            echo "访问界面: http://localhost:8000"
            echo ""
        fi
        ;;
    
    *)
        echo "无效选项"
        exit 1
        ;;
esac
