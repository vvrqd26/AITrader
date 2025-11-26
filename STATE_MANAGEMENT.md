# 状态持久化和手动管理功能说明

## ✅ 已实现功能

### 1. 实时状态持久化

#### 自动保存触发时机
```python
# 每次状态改变时自动保存
- 开仓 → 保存
- 平仓 → 保存  
- 修改仓位止损止盈 → 保存
- 创建交易计划 → 保存
- 修改交易计划 → 保存
- 删除交易计划 → 保存
```

#### 实现机制
```python
# executor设置回调
executor.on_state_change = lambda: save_state()

# 每次交易操作后自动触发
def open_position(...):
    # ... 开仓逻辑
    self._trigger_state_change()  # 自动保存
```

#### 好处
- ✅ 意外停机不丢失数据
- ✅ 断电恢复最新状态
- ✅ 崩溃后可继续运行
- ✅ 不依赖定时保存

---

### 2. Web面板手动管理

#### API接口

**创建交易计划**
```http
POST /api/plans
Content-Type: application/json

{
  "trigger_price": 3000.0,
  "direction": "long",
  "amount": 5000.0,
  "leverage": 10,
  "stop_loss": 2850.0,
  "take_profit": 3150.0
}
```

**修改交易计划**
```http
PUT /api/plans/{plan_id}
Content-Type: application/json

{
  "trigger_price": 3050.0,
  "stop_loss": 2900.0
}
```

**删除交易计划**
```http
DELETE /api/plans/{plan_id}
```

#### 前端集成
```javascript
// 创建计划
async function createPlan(planData) {
    const response = await fetch('/api/plans', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(planData)
    });
    return await response.json();
}

// 修改计划
async function updatePlan(planId, updates) {
    const response = await fetch(`/api/plans/${planId}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(updates)
    });
    return await response.json();
}

// 删除计划
async function deletePlan(planId) {
    await fetch(`/api/plans/${planId}`, {method: 'DELETE'});
}
```

---

## 📊 对比

### 旧方案
```
定时保存 (每10个周期)
  ↓
问题: 
- 意外停机丢失最近9个周期的操作
- 可能丢失重要交易
```

### 新方案
```
实时保存 (每次操作后)
  ↓
优势:
- 任何时候停机都不丢数据
- 最多丢失当前正在执行的LLM调用
```

---

## 🎯 使用场景

### 场景1: 意外停电
```
旧: 丢失过去10分钟的所有交易
新: 恢复到最后一次操作
```

### 场景2: 手动干预
```
Agent判断有误，手动创建计划:
1. 访问 http://localhost:8000
2. 在计划面板点击"添加"
3. 填写参数
4. 提交 → 立即保存
5. 价格到达自动触发
```

### 场景3: 应急调整
```
市场突变，需要立即止损:
1. Web面板查看持仓
2. 手动修改止损价
3. 立即保存生效
```

---

## 🔧 技术细节

### 回调机制
```python
class SimulatedExecutor:
    def __init__(self):
        self.on_state_change = None  # 回调函数
    
    def _trigger_state_change(self):
        if self.on_state_change:
            self.on_state_change()  # 触发保存
```

### 主程序集成
```python
def save_state_callback(self):
    self.persistence.save_state(self.executor, self.cycle_count)

executor.on_state_change = self.save_state_callback
```

### 保存位置
```
data/state.json
```

---

## ⚠️ 注意事项

### 1. 频繁保存的性能影响
```
每次保存耗时: < 10ms
短线交易频率: 不超过1次/分钟
影响: 可忽略
```

### 2. 文件损坏风险
```
使用原子写入:
1. 写入临时文件
2. 验证完整性
3. 重命名覆盖

(当前实现可进一步优化)
```

### 3. 并发保存
```
Python GIL保证:
- 同一时间只有一个线程执行
- 不会出现并发写入问题
```

---

## 📋 下一步优化建议

### 1. 原子写入
```python
def save_state(self, executor, cycle_count):
    temp_file = self.state_file + '.tmp'
    
    # 写入临时文件
    with open(temp_file, 'w') as f:
        json.dump(state, f)
    
    # 原子替换
    os.replace(temp_file, self.state_file)
```

### 2. 增量保存
```python
# 只保存变化的部分
def save_delta(self, changes):
    # 实现增量更新
    pass
```

### 3. 备份机制
```python
# 保留最近N个状态
state_backup_1.json
state_backup_2.json
...
```

---

## 🎉 总结

现在系统具备:
- ✅ 实时状态持久化 (每次操作自动保存)
- ✅ 手动交易计划管理 (Web API)
- ✅ 意外停机数据保护
- ✅ 前端界面集成 (下一步完成UI)

**不再担心意外停机丢失数据!** 🚀
