from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import json
from datetime import datetime

class PlanCreate(BaseModel):
    trigger_price: float
    direction: str
    amount: float
    leverage: int
    stop_loss: float
    take_profit: float

class PlanUpdate(BaseModel):
    trigger_price: Optional[float] = None
    amount: Optional[float] = None
    leverage: Optional[int] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class WebPanel:
    def __init__(self):
        self.app = FastAPI(title="AI Trader Panel")
        self.active_connections: List[WebSocket] = []
        self.executor = None
        self.alert_manager = None
        self.state_data = {
            "account": {},
            "positions": [],
            "plans": [],
            "price_alerts": [],
            "decisions": [],
            "system_status": {
                "status": "stopped",
                "cycle": 0,
                "last_decision_time": None,
                "api_status": {"deepseek": "unknown", "gateio": "unknown"}
            },
            "equity_history": []
        }
        
        self._setup_routes()
    
    def set_executor(self, executor, alert_manager=None):
        """设置executor和alert_manager引用，用于手动操作"""
        self.executor = executor
        self.alert_manager = alert_manager
    
    def _setup_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def get_index():
            return HTMLResponse(self._generate_html())
        
        @self.app.get("/api/state")
        async def get_state():
            return self.state_data
        
        @self.app.post("/api/plans")
        async def create_plan(plan: PlanCreate):
            """创建交易计划"""
            if not self.executor:
                raise HTTPException(status_code=500, detail="Executor未初始化")
            
            result = self.executor.create_plan(
                symbol=self.executor.positions.get(list(self.executor.positions.keys())[0]).symbol if self.executor.positions else "ETH/USDT",
                trigger_price=plan.trigger_price,
                direction=plan.direction,
                amount=plan.amount,
                leverage=plan.leverage,
                stop_loss=plan.stop_loss,
                take_profit=plan.take_profit
            )
            
            if not result.get('success'):
                raise HTTPException(status_code=400, detail=result.get('error', '创建失败'))
            
            return result
        
        @self.app.put("/api/plans/{plan_id}")
        async def update_plan(plan_id: str, plan: PlanUpdate):
            """修改交易计划"""
            if not self.executor:
                raise HTTPException(status_code=500, detail="Executor未初始化")
            
            kwargs = {k: v for k, v in plan.dict().items() if v is not None}
            result = self.executor.modify_plan(plan_id, **kwargs)
            
            if not result.get('success'):
                raise HTTPException(status_code=400, detail=result.get('error', '修改失败'))
            
            return result
        
        @self.app.delete("/api/plans/{plan_id}")
        async def delete_plan(plan_id: str):
            """删除交易计划"""
            if not self.executor:
                raise HTTPException(status_code=500, detail="Executor未初始化")
            
            result = self.executor.cancel_plan(plan_id)
            
            if not result.get('success'):
                raise HTTPException(status_code=400, detail=result.get('error', '删除失败'))
            
            return result
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                await websocket.send_json(self.state_data)
                
                while True:
                    await asyncio.sleep(1)
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
    
    async def broadcast_update(self, data: Dict):
        """广播更新到所有连接的WebSocket客户端"""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                pass
    
    def update_account(self, account_info: Dict):
        """更新账户信息"""
        self.state_data["account"] = account_info
        self.state_data["equity_history"].append({
            "timestamp": datetime.now().isoformat(),
            "equity": account_info.get("equity", 0)
        })
        
        if len(self.state_data["equity_history"]) > 1000:
            self.state_data["equity_history"] = self.state_data["equity_history"][-1000:]
    
    def update_positions(self, positions: List[Dict]):
        """更新持仓"""
        self.state_data["positions"] = positions
    
    def update_plans(self, plans: List[Dict]):
        """更新交易计划"""
        self.state_data["plans"] = plans
    
    def update_price_alerts(self, alerts: List[Dict]):
        """更新价格预警"""
        self.state_data["price_alerts"] = alerts
    
    def add_decision(self, decision: Dict):
        """添加决策记录"""
        self.state_data["decisions"].insert(0, {
            "timestamp": datetime.now().isoformat(),
            **decision
        })
        
        if len(self.state_data["decisions"]) > 50:
            self.state_data["decisions"] = self.state_data["decisions"][:50]
    
    def update_system_status(self, status: str = None, cycle: int = None,
                           last_decision_time: str = None, api_status: Dict = None):
        """更新系统状态"""
        if status:
            self.state_data["system_status"]["status"] = status
        if cycle is not None:
            self.state_data["system_status"]["cycle"] = cycle
        if last_decision_time:
            self.state_data["system_status"]["last_decision_time"] = last_decision_time
        if api_status:
            self.state_data["system_status"]["api_status"].update(api_status)
    
    def _generate_html(self) -> str:
        """生成简单的HTML界面"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>AI Trader Panel</title>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Courier New', monospace; 
            background: #0a0e27; 
            color: #00ff41; 
            padding: 20px;
            font-size: 14px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        h1 { 
            text-align: center; 
            margin-bottom: 30px; 
            color: #00ff41;
            text-shadow: 0 0 10px #00ff41;
        }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(2, 1fr); 
            gap: 20px;
            margin-bottom: 20px;
        }
        .panel { 
            background: #0d1117; 
            border: 1px solid #30363d; 
            border-radius: 6px; 
            padding: 20px;
        }
        .panel h2 { 
            color: #58a6ff; 
            margin-bottom: 15px; 
            font-size: 18px;
            border-bottom: 1px solid #30363d;
            padding-bottom: 10px;
        }
        .stat { 
            display: flex; 
            justify-content: space-between; 
            margin: 10px 0;
            padding: 8px;
            background: #161b22;
            border-radius: 4px;
        }
        .stat-label { color: #8b949e; }
        .stat-value { 
            color: #00ff41; 
            font-weight: bold;
        }
        .positive { color: #3fb950; }
        .negative { color: #f85149; }
        .position, .plan { 
            background: #161b22; 
            padding: 12px; 
            margin: 10px 0; 
            border-radius: 4px;
            border-left: 3px solid #30363d;
        }
        .position.long { border-left-color: #3fb950; }
        .position.short { border-left-color: #f85149; }
        .plan { border-left-color: #d29922; }
        .decision { 
            background: #161b22; 
            padding: 12px; 
            margin: 10px 0; 
            border-radius: 4px;
            border-left: 3px solid #58a6ff;
        }
        .markdown-content {
            white-space: pre-wrap;
            line-height: 1.5;
        }
        .markdown-content ul, .markdown-content ol {
            padding-left: 20px;
            margin: 10px 0;
        }
        .markdown-content li {
            margin: 5px 0;
        }
        .markdown-content strong {
            color: #00ff41;
        }
        .status { 
            display: inline-block; 
            padding: 4px 12px; 
            border-radius: 12px; 
            font-size: 12px;
            background: #1f6feb;
            color: white;
        }
        .status.running { background: #3fb950; }
        .status.stopped { background: #8b949e; }
        .status.error { background: #f85149; }
        pre { 
            background: #161b22; 
            padding: 10px; 
            border-radius: 4px; 
            overflow-x: auto;
            font-size: 12px;
        }
        .chart-placeholder {
            height: 200px;
            background: #161b22;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #8b949e;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin: 5px;
        }
        .btn-primary {
            background: #1f6feb;
            color: white;
        }
        .btn-success {
            background: #3fb950;
            color: white;
        }
        .btn-danger {
            background: #f85149;
            color: white;
        }
        .btn-cancel {
            background: #8b949e;
            color: white;
        }
        .btn:hover {
            opacity: 0.8;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.7);
        }
        .modal-content {
            background-color: #0d1117;
            margin: 5% auto;
            padding: 30px;
            border: 1px solid #30363d;
            border-radius: 8px;
            width: 500px;
            max-width: 90%;
        }
        .modal-content h2 {
            color: #58a6ff;
            margin-bottom: 20px;
        }
        .close {
            color: #8b949e;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: #f85149;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #8b949e;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 8px;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 4px;
            color: #00ff41;
            font-size: 14px;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #58a6ff;
        }
        .form-actions {
            margin-top: 20px;
            text-align: right;
        }
        .plan-actions {
            margin-top: 8px;
        }
        .plan-actions button {
            padding: 4px 12px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI TRADER PANEL</h1>
        
        <div class="panel" style="margin-bottom: 20px;">
            <h2>⚡ System Status</h2>
            <div class="stat">
                <span class="stat-label">Status:</span>
                <span class="stat-value"><span id="status" class="status">-</span></span>
            </div>
            <div class="stat">
                <span class="stat-label">Cycle:</span>
                <span class="stat-value" id="cycle">-</span>
            </div>
            <div class="stat">
                <span class="stat-label">Last Decision:</span>
                <span class="stat-value" id="last-decision">-</span>
            </div>
        </div>

        <div class="grid">
            <div class="panel">
                <h2>💰 Account</h2>
                <div class="stat">
                    <span class="stat-label">Total Balance:</span>
                    <span class="stat-value" id="total-balance">$0.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Available:</span>
                    <span class="stat-value" id="available">$0.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Margin Used:</span>
                    <span class="stat-value" id="margin-used">$0.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Unrealized PnL:</span>
                    <span class="stat-value" id="unrealized-pnl">$0.00</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Equity:</span>
                    <span class="stat-value" id="equity">$0.00</span>
                </div>
            </div>

            <div class="panel">
                <h2>📈 Equity Chart</h2>
                <div class="chart-placeholder">Chart: equity history visualization</div>
            </div>
        </div>

        <div class="grid">
            <div class="panel">
                <h2>📊 Positions</h2>
                <div id="positions">No positions</div>
            </div>

            <div class="panel">
                <h2>📝 Trading Plans</h2>
                <div style="margin-bottom: 15px;">
                    <button onclick="showCreatePlanModal()" class="btn btn-primary">➕ 创建计划</button>
                </div>
                <div id="plans">No plans</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="panel">
                <h2>⚡ Price Alerts</h2>
                <div id="price-alerts">No alerts</div>
            </div>

            <div class="panel">
                <h2>🧠 Agent Decisions</h2>
                <div id="decisions">No decisions yet</div>
            </div>
        </div>
    </div>
    
    <!-- 创建计划模态框 -->
    <div id="createPlanModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h2>创建交易计划</h2>
            <form id="createPlanForm" onsubmit="createPlan(event)">
                <div class="form-group">
                    <label>触发价格:</label>
                    <input type="number" step="0.01" name="trigger_price" required>
                </div>
                <div class="form-group">
                    <label>方向:</label>
                    <select name="direction" required>
                        <option value="long">做多 (LONG)</option>
                        <option value="short">做空 (SHORT)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>金额 (USD):</label>
                    <input type="number" step="0.01" name="amount" required>
                </div>
                <div class="form-group">
                    <label>杠杆:</label>
                    <input type="number" step="1" name="leverage" value="10" min="1" max="20" required>
                </div>
                <div class="form-group">
                    <label>止损价格:</label>
                    <input type="number" step="0.01" name="stop_loss" required>
                </div>
                <div class="form-group">
                    <label>止盈价格:</label>
                    <input type="number" step="0.01" name="take_profit" required>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn btn-success">创建</button>
                    <button type="button" class="btn btn-cancel" onclick="closeModal()">取消</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updateUI(data);
        };

        function updateUI(data) {
            // System status
            const status = data.system_status.status;
            document.getElementById('status').textContent = status.toUpperCase();
            document.getElementById('status').className = 'status ' + status;
            document.getElementById('cycle').textContent = data.system_status.cycle;
            document.getElementById('last-decision').textContent = 
                data.system_status.last_decision_time || '-';

            // Account
            const acc = data.account;
            document.getElementById('total-balance').textContent = 
                '$' + (acc.total_balance || 0).toFixed(2);
            document.getElementById('available').textContent = 
                '$' + (acc.available || 0).toFixed(2);
            document.getElementById('margin-used').textContent = 
                '$' + (acc.margin_used || 0).toFixed(2);
            
            const pnl = acc.unrealized_pnl || 0;
            const pnlEl = document.getElementById('unrealized-pnl');
            pnlEl.textContent = '$' + pnl.toFixed(2);
            pnlEl.className = 'stat-value ' + (pnl >= 0 ? 'positive' : 'negative');
            
            document.getElementById('equity').textContent = 
                '$' + (acc.equity || 0).toFixed(2);

            // Positions
            const posDiv = document.getElementById('positions');
            if (data.positions.length === 0) {
                posDiv.innerHTML = '<div style="color: #8b949e;">No positions</div>';
            } else {
                posDiv.innerHTML = data.positions.map(pos => `
                    <div class="position ${pos.direction}">
                        <div><strong>${pos.position_id}</strong> - ${pos.direction.toUpperCase()} 
                        $${pos.amount.toFixed(2)} @ ${pos.leverage}x</div>
                        <div>Entry: $${pos.entry_price.toFixed(2)} | 
                        Current: $${(pos.current_price || 0).toFixed(2)}</div>
                        <div class="${pos.pnl_percent >= 0 ? 'positive' : 'negative'}">
                        PnL: $${pos.unrealized_pnl.toFixed(2)} (${pos.pnl_percent.toFixed(2)}%)</div>
                        <div>SL: $${pos.stop_loss.toFixed(2)} | TP: $${pos.take_profit.toFixed(2)}</div>
                    </div>
                `).join('');
            }

            // Plans
            const plansDiv = document.getElementById('plans');
            if (data.plans.length === 0) {
                plansDiv.innerHTML = '<div style="color: #8b949e;">No plans</div>';
            } else {
                plansDiv.innerHTML = data.plans.map(plan => `
                    <div class="plan">
                        <div><strong>${plan.plan_id}</strong> - Trigger: $${plan.trigger_price.toFixed(2)}</div>
                        <div>${plan.direction.toUpperCase()} $${plan.amount.toFixed(2)} @ ${plan.leverage}x</div>
                        <div>SL: $${plan.stop_loss.toFixed(2)} | TP: $${plan.take_profit.toFixed(2)}</div>
                        <div class="plan-actions">
                            <button class="btn btn-danger" onclick="deletePlan('${plan.plan_id}')">🗑️ 删除</button>
                        </div>
                    </div>
                `).join('');
            }

            // Price Alerts
            const alertsDiv = document.getElementById('price-alerts');
            if (data.price_alerts.length === 0) {
                alertsDiv.innerHTML = '<div style="color: #8b949e;">No alerts</div>';
            } else {
                alertsDiv.innerHTML = data.price_alerts.map(alert => `
                    <div class="plan">
                        <div><strong>${alert.alert_id}</strong> - ${alert.condition.toUpperCase()} $${alert.price.toFixed(2)}</div>
                        <div>${alert.description || '无描述'}</div>
                        <div style="font-size: 12px; color: #8b949e;">创建时间: ${new Date(alert.create_time).toLocaleString()}</div>
                    </div>
                `).join('');
            }

            // Decisions
            const decisionsDiv = document.getElementById('decisions');
            if (data.decisions.length === 0) {
                decisionsDiv.innerHTML = '<div style="color: #8b949e;">No decisions yet</div>';
            } else {
                decisionsDiv.innerHTML = data.decisions.slice(0, 10).map(dec => {
                    const analysisHtml = dec.analysis ? marked.parse(dec.analysis) : 'No analysis';
                    return `
                        <div class="decision">
                            <div><strong>${dec.timestamp}</strong></div>
                            <div class="markdown-content">${analysisHtml}</div>
                            ${dec.tool_calls && dec.tool_calls.length > 0 ? 
                                '<pre>' + JSON.stringify(dec.tool_calls, null, 2) + '</pre>' : 
                                '<div style="color: #8b949e;">No actions</div>'}
                        </div>
                    `;
                }).join('');
            }
        }
        
        // 模态框控制
        function showCreatePlanModal() {
            document.getElementById('createPlanModal').style.display = 'block';
        }
        
        function closeModal() {
            document.getElementById('createPlanModal').style.display = 'none';
            document.getElementById('createPlanForm').reset();
        }
        
        window.onclick = function(event) {
            const modal = document.getElementById('createPlanModal');
            if (event.target == modal) {
                closeModal();
            }
        }
        
        // 创建计划
        async function createPlan(event) {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            const planData = {
                trigger_price: parseFloat(formData.get('trigger_price')),
                direction: formData.get('direction'),
                amount: parseFloat(formData.get('amount')),
                leverage: parseInt(formData.get('leverage')),
                stop_loss: parseFloat(formData.get('stop_loss')),
                take_profit: parseFloat(formData.get('take_profit'))
            };
            
            try {
                const response = await fetch('/api/plans', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(planData)
                });
                
                const result = await response.json();
                
                if (response.ok && result.success) {
                    alert('计划创建成功: ' + result.plan_id);
                    closeModal();
                    location.reload();
                } else {
                    alert('创建失败: ' + (result.error || result.detail || '未知错误'));
                }
            } catch (error) {
                alert('请求失败: ' + error.message);
            }
        }
        
        // 删除计划
        async function deletePlan(planId) {
            if (!confirm('确定要删除这个计划吗？')) {
                return;
            }
            
            try {
                const response = await fetch(`/api/plans/${planId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (response.ok && result.success) {
                    alert('计划已删除');
                    location.reload();
                } else {
                    alert('删除失败: ' + (result.error || result.detail || '未知错误'));
                }
            } catch (error) {
                alert('请求失败: ' + error.message);
            }
        }

        ws.onerror = function(error) {
            console.error('WebSocket error:', error);
        };

        ws.onclose = function() {
            console.log('WebSocket connection closed');
            setTimeout(() => location.reload(), 5000);
        };
    </script>
</body>
</html>
"""