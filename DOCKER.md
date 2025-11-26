# AI Trader - Docker 部署指南

## 快速部署到绿联NAS (Intel N100)

### 方法一: 本地构建后导入到NAS

#### 1. 在本地构建镜像

```bash
# 构建Docker镜像
./build_docker.sh

# 导出镜像文件
./export_image.sh
```

这将生成 `ai-trader-image.tar` 文件 (约1-2GB)

#### 2. 传输到NAS

将以下文件上传到NAS:
- `ai-trader-image.tar` (镜像文件)
- `docker-compose.yml`
- `config/` 目录 (配置文件)

```bash
# 使用scp传输 (替换NAS_IP为你的NAS IP地址)
scp ai-trader-image.tar docker-compose.yml user@NAS_IP:/path/to/ai-trader/
scp -r config user@NAS_IP:/path/to/ai-trader/
```

#### 3. 在NAS上导入并启动

SSH登录到NAS后:

```bash
# 导入镜像
docker load -i ai-trader-image.tar

# 编辑配置文件
vim config/config.json
# 填入 DeepSeek API Key

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 4. 访问Web界面

浏览器打开: `http://NAS_IP:8000`

---

### 方法二: 直接在NAS上构建

如果NAS支持Docker构建:

```bash
# 1. 上传整个项目目录到NAS
scp -r /path/to/ai-trader user@NAS_IP:/volume1/docker/

# 2. SSH登录NAS
ssh user@NAS_IP

# 3. 进入项目目录
cd /volume1/docker/ai-trader

# 4. 构建镜像
./build_docker.sh

# 5. 启动
docker-compose up -d
```

---

## Docker 命令参考

### 启动/停止

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看状态
docker-compose ps
```

### 日志查看

```bash
# 实时日志
docker-compose logs -f

# 最近100行
docker-compose logs --tail=100

# 仅查看错误
docker-compose logs | grep ERROR
```

### 进入容器

```bash
# 进入容器Shell
docker-compose exec ai-trader bash

# 查看状态文件
docker-compose exec ai-trader python view_state.py
```

### 数据备份

```bash
# 备份配置和数据
tar -czf ai-trader-backup-$(date +%Y%m%d).tar.gz config/ data/ logs/

# 恢复
tar -xzf ai-trader-backup-20251126.tar.gz
```

---

## 目录结构 (NAS上)

```
/volume1/docker/ai-trader/
├── docker-compose.yml    # Docker编排文件
├── config/               # 配置目录 (挂载)
│   └── config.json       # 配置文件
├── data/                 # 数据目录 (挂载)
│   ├── cache/            # 行情缓存
│   └── state.json        # 状态文件
└── logs/                 # 日志目录 (挂载)
    ├── decision.log
    ├── trades.log
    └── system.log
```

---

## 端口映射

- `8000` - Web管理界面

可在 `docker-compose.yml` 中修改端口:
```yaml
ports:
  - "8080:8000"  # 改为8080端口
```

---

## 环境变量

可在 `docker-compose.yml` 中配置:

```yaml
environment:
  - TZ=Asia/Shanghai           # 时区
  - PYTHONUNBUFFERED=1         # Python输出缓冲
```

---

## 资源限制 (可选)

在 `docker-compose.yml` 中添加:

```yaml
services:
  ai-trader:
    # ... 其他配置 ...
    deploy:
      resources:
        limits:
          cpus: '2.0'      # 限制使用2个CPU核心
          memory: 2G       # 限制内存2GB
        reservations:
          cpus: '0.5'
          memory: 512M
```

---

## 自动启动

Docker Compose 配置了 `restart: unless-stopped`，容器会:
- NAS重启后自动启动
- 容器崩溃后自动重启
- 手动停止后不会自动启动

---

## 更新镜像

```bash
# 1. 停止旧容器
docker-compose down

# 2. 删除旧镜像
docker rmi ai-trader:latest

# 3. 导入新镜像
docker load -i ai-trader-image-new.tar

# 4. 启动新容器
docker-compose up -d
```

---

## 故障排查

### 容器无法启动

```bash
# 查看容器日志
docker-compose logs

# 检查配置文件
cat config/config.json

# 检查端口占用
netstat -tulpn | grep 8000
```

### 无法访问Web界面

1. 检查防火墙是否开放8000端口
2. 检查容器是否正在运行: `docker-compose ps`
3. 检查日志: `docker-compose logs`

### 数据丢失

数据持久化在宿主机的 `data/` 目录，容器删除不会丢失

---

## 性能优化

### 1. 使用本地镜像源

编辑 `Dockerfile`:
```dockerfile
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ...
```

### 2. 减小镜像体积

已使用 `python:3.11-slim` 基础镜像，体积约500MB

### 3. 日志轮转

日志文件会自动轮转 (100MB滚动)

---

## 安全建议

1. **不要暴露到公网**: 仅在局域网访问
2. **定期备份**: 备份 `config/` 和 `data/`
3. **API密钥保护**: 不要提交到Git
4. **更新依赖**: 定期更新Python包

---

## 卸载

```bash
# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi ai-trader:latest

# 删除数据 (谨慎!)
rm -rf config/ data/ logs/
```

---

## 联系与支持

- 查看日志: `docker-compose logs -f`
- 进入容器调试: `docker-compose exec ai-trader bash`
- 检查状态: `docker-compose exec ai-trader python view_state.py`
