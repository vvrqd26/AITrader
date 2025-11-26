from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Dict
import asyncio
import json
from datetime import datetime

class WebPanel:
    def __init__(self):
        self.app = FastAPI(title="AI Trader Panel")
        self.active_connections: List[WebSocket] = []
        self.state_data = {
            "account": {},
            "positions": [],
            "plans": [],
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
    
    def _setup_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def get_index():
            return HTMLResponse(self._generate_html())
        
        @self.app.get("/api/state")
        async def get_state():
            return self.state_data
        
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
        .position, .plan, .decision { 
            background: #161b22; 
            padding: 12px; 
            margin: 10px 0; 
            border-radius: 4px;
            border-left: 3px solid #30363d;
        }
        .position.long { border-left-color: #3fb950; }
        .position.short { border-left-color: #f85149; }
        .decision { border-left-color: #58a6ff; }
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
                <div id="plans">No plans</div>
            </div>
        </div>

        <div class="panel">
            <h2>🧠 Agent Decisions</h2>
            <div id="decisions">No decisions yet</div>
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
                    </div>
                `).join('');
            }

            // Decisions
            const decisionsDiv = document.getElementById('decisions');
            if (data.decisions.length === 0) {
                decisionsDiv.innerHTML = '<div style="color: #8b949e;">No decisions yet</div>';
            } else {
                decisionsDiv.innerHTML = data.decisions.slice(0, 10).map(dec => `
                    <div class="decision">
                        <div><strong>${dec.timestamp}</strong></div>
                        <div>${dec.analysis || 'No analysis'}</div>
                        ${dec.tool_calls && dec.tool_calls.length > 0 ? 
                            '<pre>' + JSON.stringify(dec.tool_calls, null, 2) + '</pre>' : 
                            '<div style="color: #8b949e;">No actions</div>'}
                    </div>
                `).join('');
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