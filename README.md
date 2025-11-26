# AI Trader - 使用说明

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**使用国内镜像源加速安装**:
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

**注意**: `ta-lib` 需要先安装系统依赖:

- **macOS**: `brew install ta-lib`
- **Ubuntu**: `sudo apt-get install ta-lib`
- **Windows**: 下载预编译包 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib

### 2. 配置文件

编辑 `config/config.json`:

```json
{
  "api_keys": {
    "deepseek": "your-deepseek-api-key",
    "gateio_key": "",
    "gateio_secret": ""
  }
}
```

**获取API密钥**:
- DeepSeek: https://platform.deepseek.com/ (必需)
- Gate.io: 仅获取行情数据不需要API密钥，留空即可

### 3. 启动系统

```bash
python main.py
```

系统将启动:
- 主决策循环 (默认60秒一次)
- 交易计划监控线程 (每秒检查)
- Web面板服务器 (http://localhost:8000)

### 4. 访问Web面板

打开浏览器访问: http://localhost:8000

面板显示:
- 账户信息和权益曲线
- 当前持仓
- 待触发计划
- Agent决策记录
- 系统状态

## 配置说明

### 交易配置

- `symbol`: 交易对 (如 `BTC_USDT`)
- `initial_balance`: 初始资金 (默认 100,000 USD)
- `fee_rate`: 手续费率 (默认 0.0001 = 0.01%)
- `max_position_ratio`: 单笔最大仓位 (默认 0.3 = 30%)
- `max_leverage`: 最大杠杆 (默认 20倍)
- `min_stop_loss_percent`: 最小止损距离 (默认 0.05 = 5%)

### 指标配置

- `timeframes`: 时间周期列表 (如 `["15m", "1h", "4h", "1d", "1w"]`)
- `types`: 指标类型 (MA, EMA, MACD, RSI, BOLL, KDJ, ATR, OBV)
- `ma_periods`: MA周期参数
- `rsi_period`: RSI周期
- `macd_params`: MACD参数 [快线, 慢线, 信号线]

### 循环配置

- `interval`: 主循环间隔 (秒, 默认60)
- `plan_check_interval`: 计划检查间隔 (秒, 默认1)

### Agent配置

- `system_prompt`: Agent的系统提示词 (定义交易风格)

## 日志文件

日志位于 `logs/` 目录:

- `decision.log`: 决策日志 (JSON格式)
- `trades.log`: 交易日志 (JSON格式)
- `system.log`: 系统日志 (文本格式)

## 目录结构

```
.
├── config/
│   └── config.json          # 配置文件
├── src/
│   ├── executor/            # 模拟交易执行器
│   ├── collector/           # 市场数据收集器
│   ├── mcp/                 # MCP工具服务器
│   ├── agent/               # AI Agent
│   ├── logger/              # 日志系统
│   ├── web/                 # Web面板
│   └── config.py            # 配置加载器
├── logs/                    # 日志目录
├── data/                    # 数据缓存目录
├── main.py                  # 主程序
├── requirements.txt         # 依赖列表
└── README.md               # 项目说明
```

## 常见问题

### 1. 无法连接Gate.io API

检查:
- API密钥是否正确
- 网络连接是否正常
- Gate.io API是否有访问限制

### 2. DeepSeek API调用失败

检查:
- API密钥是否有效
- 账户余额是否充足
- 是否触发限流

### 3. TA-Lib安装失败

参考: https://github.com/TA-Lib/ta-lib-python

### 4. 程序崩溃

检查 `logs/system.log` 查看错误信息

## 停止系统

按 `Ctrl+C` 优雅停止系统

**系统会自动保存状态**:
- 每10个周期自动保存一次
- 停止时保存最终状态
- 下次启动时自动恢复

## 状态管理

### 查看保存的状态

```bash
python view_state.py
```

显示:
- 保存时间
- 当前周期数
- 账户余额
- 持仓列表
- 交易计划
- 历史交易数

### 重置状态

如果想从头开始，可以:

```bash
python view_state.py
# 然后选择 'y' 删除状态文件
```

或直接删除:
```bash
rm data/state.json
```

## 注意事项

⚠️ **这是实验性项目，仅用于模拟交易！**

- 当前只支持模拟交易，不涉及真实资金
- Agent决策具有不确定性，请勿直接用于实盘
- 定期检查日志，根据运行情况优化Agent的Prompt
- 建议先观察运行一段时间，评估策略有效性

## 优化建议

1. **调整Agent Prompt**: 根据决策日志优化 `system_prompt`
2. **修改风险参数**: 调整止损距离、仓位限制等
3. **增加指标**: 在 `indicators.types` 中添加更多技术指标
4. **调整周期**: 修改 `loop.interval` 改变决策频率

## 开发

### 添加新指标

在 `src/collector/market_data.py` 的 `IndicatorCalculator` 类中添加:

```python
@staticmethod
def calculate_new_indicator(df: pd.DataFrame) -> pd.DataFrame:
    # 计算逻辑
    df['NEW_INDICATOR'] = ...
    return df
```

### 添加新工具

在 `src/mcp/mcp_server.py` 的 `_define_tools` 方法中添加工具定义

## 联系

如有问题或建议，请查看项目文档或提交Issue

---

## Docker 部署

### 快速部署到NAS

```bash
# 一键部署脚本
./deploy.sh
```

详细的Docker部署文档请查看: [DOCKER.md](DOCKER.md)

**绿联NAS用户**:
1. 本地运行 `./deploy.sh` 选择选项1
2. 上传生成的 `ai-trader-image.tar` 到NAS
3. 在NAS上导入镜像并启动

**简化流程**:
```bash
# 本地构建
./build_docker.sh
./export_image.sh

# 传输到NAS
scp ai-trader-image.tar user@NAS_IP:/volume1/docker/
scp docker-compose.yml user@NAS_IP:/volume1/docker/ai-trader/
scp -r config user@NAS_IP:/volume1/docker/ai-trader/

# NAS上执行
ssh user@NAS_IP
cd /volume1/docker/ai-trader
docker load -i ../ai-trader-image.tar
docker-compose up -d
```

访问: http://NAS_IP:8000