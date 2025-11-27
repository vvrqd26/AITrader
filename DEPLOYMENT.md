# AI Trader 部署指南

## 本地部署方式

```bash
# 1. 克隆代码
git clone https://github.com/your-repo/ai-trader.git
cd ai-trader

# 2. 编辑配置
vim config/config.json

# 3. 启动服务
docker-compose up -d
```

## 远程一键部署方式

```bash
# 下载部署脚本
wget https://raw.githubusercontent.com/your-repo/ai-trader/main/deploy-remote.sh

# 添加执行权限
chmod +x deploy-remote.sh

# 运行部署脚本
./deploy-remote.sh
```

部署过程中会提示输入Git仓库URL和分支名称。

## 配置说明

首次运行前需要配置：
- `config/config.json`: API密钥、交易参数等
- `config/strategies/`: 交易策略文件(可选)

## 访问面板

部署完成后访问: http://localhost:8000

## 更新代码

```bash
# 拉取最新代码并重启服务
docker-compose down
docker-compose up -d --build
```