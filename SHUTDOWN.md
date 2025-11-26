# 优雅关闭流程说明

## 问题分析

当你按 `Ctrl+C` 停止程序时看到的提示:

```
^CINFO:     Shutting down
INFO:     connection closed
INFO:     Waiting for background tasks to complete. (CTRL+C to force quit)
```

这表示系统正在执行**优雅关闭**流程。

## 原因

系统有3个并发运行的组件:

1. **Web服务器** (Uvicorn FastAPI)
   - 监听 8000 端口
   - 处理HTTP/WebSocket连接

2. **WebSocket价格推送**
   - 保持与Gate.io的长连接
   - 实时接收价格更新

3. **主决策循环**
   - 定期执行交易决策
   - 可能正在进行LLM调用

按 `Ctrl+C` 后，这些任务需要**有序停止**。

## 等待的任务

### 1. WebSocket连接关闭
```
connection closed  ← 正在关闭与Gate.io的WebSocket连接
```

### 2. 后台任务完成
```
Waiting for background tasks to complete
```

可能在等待:
- WebSocket消息处理完成
- 价格更新回调执行完成
- 状态保存操作
- 日志写入磁盘

### 3. 如果卡住

如果超过5秒还在等待，可以:
```
再次按 Ctrl+C 强制退出
```

---

## 优化方案

已实现优雅关闭，现在流程是:

```
Ctrl+C
  ↓
1. 停止主循环 (立即)
2. 停止价格推送 (关闭WebSocket)
3. 保存最终状态
4. 停止Web服务器
5. 退出程序

总耗时: < 2秒
```

## 关闭日志输出

现在你会看到:

```
^C
[INFO] 检测到 Ctrl+C
[INFO] 收到关闭信号，正在停止系统...
[INFO] 停止价格推送...
[INFO] 保存最终状态...
[INFO] 状态已保存 (周期 X)
[INFO] 停止Web服务器...
[INFO] 系统已停止
```

清晰明了，知道每一步在做什么。

---

## 为什么需要优雅关闭?

### ❌ 强制退出的问题
```python
kill -9 <pid>  # 立即杀死
```

后果:
- ❌ WebSocket连接未关闭 (服务器资源泄漏)
- ❌ 状态未保存 (数据丢失)
- ❌ 持仓信息丢失
- ❌ 日志未写入

### ✅ 优雅关闭的好处
```python
Ctrl+C  # 发送SIGINT信号
```

保证:
- ✅ 所有连接正确关闭
- ✅ 状态完整保存
- ✅ 持仓信息持久化
- ✅ 日志完整记录
- ✅ 下次启动可恢复

---

## 技术细节

### 关闭顺序
```python
1. 设置 self.running = False
   → 主循环检测到后退出

2. price_stream.stop()
   → WebSocket检测到后断开连接

3. price_stream_task.cancel()
   → 取消异步任务

4. persistence.save_state()
   → 保存到 data/state.json

5. server.shutdown()
   → 关闭Web服务器
```

### 超时处理
- 每个步骤有隐式超时
- 如果卡住，再按一次 `Ctrl+C` 强制退出
- Uvicorn会显示提示信息

---

## 最佳实践

### 正常停止
```bash
# 按一次 Ctrl+C
# 等待 1-2 秒
# 看到 "系统已停止" 后完成
```

### 强制停止
```bash
# 按两次 Ctrl+C (快速连按)
# 或者等待超时后再按
```

### 查看状态
```bash
# 停止后查看是否保存成功
python view_state.py
```

---

## 改进后的体验

**旧版本**:
```
^C (什么都不显示，卡住10秒)
Waiting for background tasks...
(不知道在等什么)
```

**新版本**:
```
^C
[INFO] 检测到 Ctrl+C
[INFO] 停止价格推送...
[INFO] 保存最终状态...
[INFO] 停止Web服务器...
[INFO] 系统已停止

总耗时: 1.2秒
```

清晰、快速、可控! 🎉
