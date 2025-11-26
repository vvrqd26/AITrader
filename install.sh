#!/bin/bash

echo "================================"
echo "  AI Trader 安装脚本"
echo "================================"
echo ""

echo "检查 Python 版本..."
python3 --version
if [ $? -ne 0 ]; then
    echo "错误: 未找到 Python 3，请先安装 Python 3.10+"
    exit 1
fi

echo ""
echo "检查 TA-Lib 系统依赖..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        echo "警告: 未找到 Homebrew，请手动安装 TA-Lib"
        echo "访问: https://github.com/TA-Lib/ta-lib-python"
    else
        echo "尝试安装 TA-Lib (需要 Homebrew)..."
        brew install ta-lib
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "尝试安装 TA-Lib (需要 sudo)..."
    sudo apt-get update
    sudo apt-get install -y ta-lib
else
    echo "警告: Windows 用户请手动安装 TA-Lib"
    echo "下载地址: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib"
fi

echo ""
echo "创建虚拟环境 (可选，推荐)..."
read -p "是否创建虚拟环境? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 -m venv venv
    echo "虚拟环境已创建，请运行: source venv/bin/activate"
    source venv/bin/activate
fi

echo ""
echo "安装 Python 依赖..."
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

echo ""
echo "================================"
echo "  安装完成!"
echo "================================"
echo ""
echo "下一步:"
echo "1. 编辑 config/config.json 填入 API 密钥"
echo "2. 运行: python main.py"
echo "3. 访问: http://localhost:8000"
echo ""