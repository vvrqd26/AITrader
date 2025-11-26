import json
import os
from datetime import datetime
from typing import Dict, Any

class StatePersistence:
    def __init__(self, state_file: str = "data/state.json"):
        self.state_file = state_file
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
    
    def save_state(self, executor, cycle_count: int, alert_manager=None) -> bool:
        """保存当前状态"""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "cycle_count": cycle_count,
                "executor": {
                    "total_balance": executor.total_balance,
                    "last_price": executor.last_price,
                    "positions": self._serialize_positions(executor.positions),
                    "plans": self._serialize_plans(executor.plans),
                    "trade_history": executor.trade_history[-100:]
                }
            }
            
            # 保存价格预警
            if alert_manager:
                state["price_alerts"] = alert_manager.to_dict()
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2, default=str)
            
            return True
        except Exception as e:
            print(f"保存状态失败: {e}")
            return False
    
    def load_state(self) -> Dict[str, Any]:
        """加载状态"""
        if not os.path.exists(self.state_file):
            return None
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载状态失败: {e}")
            return None
    
    def restore_executor(self, executor, state: Dict, alert_manager=None, callback=None) -> int:
        """恢复执行器状态"""
        if not state or 'executor' not in state:
            return 0
        
        try:
            executor_state = state['executor']
            
            executor.total_balance = executor_state.get('total_balance', executor.initial_balance)
            executor.last_price = executor_state.get('last_price')
            
            executor.positions = self._deserialize_positions(
                executor_state.get('positions', {})
            )
            
            executor.plans = self._deserialize_plans(
                executor_state.get('plans', {})
            )
            
            executor.trade_history = executor_state.get('trade_history', [])
            
            for item in executor.trade_history:
                if 'timestamp' in item and isinstance(item['timestamp'], str):
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
            
            # 恢复价格预警
            if alert_manager and callback and 'price_alerts' in state:
                alert_manager.from_dict(state['price_alerts'], callback)
            
            cycle_count = state.get('cycle_count', 0)
            
            print(f"成功恢复状态: 周期 {cycle_count}, 余额 ${executor.total_balance:.2f}, "
                  f"{len(executor.positions)} 个持仓, {len(executor.plans)} 个计划")
            
            if alert_manager:
                alerts = alert_manager.get_active_alerts()
                print(f"{len(alerts)} 个价格预警")
            
            return cycle_count
        
        except Exception as e:
            print(f"恢复状态失败: {e}")
            return 0
    
    def _serialize_positions(self, positions: Dict) -> Dict:
        """序列化持仓"""
        result = {}
        for pos_id, pos in positions.items():
            result[pos_id] = {
                "id": pos.id,
                "symbol": pos.symbol,
                "direction": pos.direction.value,
                "entry_price": pos.entry_price,
                "amount": pos.amount,
                "leverage": pos.leverage,
                "stop_loss": pos.stop_loss,
                "take_profit": pos.take_profit,
                "open_time": pos.open_time.isoformat(),
                "status": pos.status.value,
                "close_time": pos.close_time.isoformat() if pos.close_time else None,
                "close_price": pos.close_price,
                "realized_pnl": pos.realized_pnl
            }
        return result
    
    def _deserialize_positions(self, positions_data: Dict) -> Dict:
        """反序列化持仓"""
        from src.executor import Position, Direction, PositionStatus
        
        result = {}
        for pos_id, data in positions_data.items():
            pos = Position(
                id=data['id'],
                symbol=data['symbol'],
                direction=Direction(data['direction']),
                entry_price=data['entry_price'],
                amount=data['amount'],
                leverage=data['leverage'],
                stop_loss=data['stop_loss'],
                take_profit=data['take_profit'],
                open_time=datetime.fromisoformat(data['open_time']),
                status=PositionStatus(data['status']),
                close_time=datetime.fromisoformat(data['close_time']) if data['close_time'] else None,
                close_price=data['close_price'],
                realized_pnl=data['realized_pnl']
            )
            result[pos_id] = pos
        return result
    
    def _serialize_plans(self, plans: Dict) -> Dict:
        """序列化计划"""
        result = {}
        for plan_id, plan in plans.items():
            result[plan_id] = {
                "id": plan.id,
                "symbol": plan.symbol,
                "trigger_price": plan.trigger_price,
                "direction": plan.direction.value,
                "amount": plan.amount,
                "leverage": plan.leverage,
                "stop_loss": plan.stop_loss,
                "take_profit": plan.take_profit,
                "create_time": plan.create_time.isoformat(),
                "status": plan.status.value
            }
        return result
    
    def _deserialize_plans(self, plans_data: Dict) -> Dict:
        """反序列化计划"""
        from src.executor import TradingPlan, Direction, PlanStatus
        
        result = {}
        for plan_id, data in plans_data.items():
            plan = TradingPlan(
                id=data['id'],
                symbol=data['symbol'],
                trigger_price=data['trigger_price'],
                direction=Direction(data['direction']),
                amount=data['amount'],
                leverage=data['leverage'],
                stop_loss=data['stop_loss'],
                take_profit=data['take_profit'],
                create_time=datetime.fromisoformat(data['create_time']),
                status=PlanStatus(data['status'])
            )
            result[plan_id] = plan
        return result