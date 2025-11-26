from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Callable
from enum import Enum
import uuid
import time

class Direction(Enum):
    LONG = "long"
    SHORT = "short"

class PositionStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"

class PlanStatus(Enum):
    PENDING = "pending"
    TRIGGERED = "triggered"
    CANCELLED = "cancelled"

@dataclass
class Position:
    id: str
    symbol: str
    direction: Direction
    entry_price: float
    amount: float
    leverage: int
    stop_loss: float
    take_profit: float
    open_time: datetime
    status: PositionStatus = PositionStatus.OPEN
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    realized_pnl: float = 0.0
    
    @property
    def margin_used(self) -> float:
        return self.amount / self.leverage
    
    def unrealized_pnl(self, current_price: float) -> float:
        if self.status == PositionStatus.CLOSED:
            return 0.0
        
        if self.direction == Direction.LONG:
            return (current_price - self.entry_price) * self.amount / self.entry_price
        else:
            return (self.entry_price - current_price) * self.amount / self.entry_price
    
    def check_stop_loss_take_profit(self, current_price: float) -> Optional[str]:
        if self.direction == Direction.LONG:
            if current_price <= self.stop_loss:
                return "stop_loss"
            elif current_price >= self.take_profit:
                return "take_profit"
        else:
            if current_price >= self.stop_loss:
                return "stop_loss"
            elif current_price <= self.take_profit:
                return "take_profit"
        return None

@dataclass
class TradingPlan:
    id: str
    symbol: str
    trigger_price: float
    direction: Direction
    amount: float
    leverage: int
    stop_loss: float
    take_profit: float
    create_time: datetime
    status: PlanStatus = PlanStatus.PENDING
    
    def check_trigger(self, current_price: float, last_price: float) -> bool:
        if self.status != PlanStatus.PENDING:
            return False
        
        if self.direction == Direction.LONG:
            return last_price < self.trigger_price <= current_price
        else:
            return last_price > self.trigger_price >= current_price

@dataclass
class Account:
    total_balance: float
    available: float
    margin_used: float
    unrealized_pnl: float
    
    @property
    def equity(self) -> float:
        return self.total_balance + self.unrealized_pnl

class SimulatedExecutor:
    def __init__(self, initial_balance: float, fee_rate: float, max_position_ratio: float, 
                 max_leverage: int, min_stop_loss_percent: float):
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate
        self.max_position_ratio = max_position_ratio
        self.max_leverage = max_leverage
        self.min_stop_loss_percent = min_stop_loss_percent
        
        self.total_balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.plans: Dict[str, TradingPlan] = {}
        self.trade_history: List[Dict] = []
        
        self.last_price: Optional[float] = None
        
        self.on_state_change: Optional[Callable] = None
    
    def get_account_info(self) -> Account:
        margin_used = sum(pos.margin_used for pos in self.positions.values())
        unrealized_pnl = sum(pos.unrealized_pnl(self.last_price) 
                            for pos in self.positions.values() if self.last_price)
        available = self.total_balance - margin_used
        
        return Account(
            total_balance=self.total_balance,
            available=available,
            margin_used=margin_used,
            unrealized_pnl=unrealized_pnl
        )
    
    def _trigger_state_change(self):
        """触发状态变化回调"""
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception as e:
                print(f"状态变化回调错误: {e}")
    
    def validate_position(self, amount: float, leverage: int, stop_loss: float, 
                         entry_price: float, direction: Direction) -> tuple[bool, str]:
        account = self.get_account_info()
        margin_needed = amount / leverage
        
        if margin_needed > account.available:
            return False, f"可用资金不足: 需要 {margin_needed:.2f}, 可用 {account.available:.2f}"
        
        if amount > self.total_balance * self.max_position_ratio:
            return False, f"超过单笔最大仓位限制: {self.max_position_ratio*100}%"
        
        if leverage > self.max_leverage:
            return False, f"超过最大杠杆限制: {self.max_leverage}x"
        
        stop_loss_percent = abs(entry_price - stop_loss) / entry_price
        if stop_loss_percent < self.min_stop_loss_percent:
            return False, f"止损距离过小，最小 {self.min_stop_loss_percent*100}%"
        
        if direction == Direction.LONG and stop_loss >= entry_price:
            return False, "做多时止损价必须低于开仓价"
        
        if direction == Direction.SHORT and stop_loss <= entry_price:
            return False, "做空时止损价必须高于开仓价"
        
        return True, "验证通过"
    
    def open_position(self, symbol: str, direction: str, amount: float, leverage: int,
                     stop_loss: float, take_profit: float, current_price: float) -> Dict:
        try:
            dir_enum = Direction(direction)
        except ValueError:
            return {"success": False, "error": f"无效的方向: {direction}"}
        
        valid, msg = self.validate_position(amount, leverage, stop_loss, current_price, dir_enum)
        if not valid:
            return {"success": False, "error": msg}
        
        fee = amount * self.fee_rate
        self.total_balance -= fee
        
        position = Position(
            id=f"pos_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            direction=dir_enum,
            entry_price=current_price,
            amount=amount,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            open_time=datetime.now()
        )
        
        self.positions[position.id] = position
        self.trade_history.append({
            "timestamp": datetime.now(),
            "type": "open_position",
            "position_id": position.id,
            "direction": direction,
            "entry_price": current_price,
            "amount": amount,
            "leverage": leverage,
            "fee": fee
        })
        
        self._trigger_state_change()
        
        return {
            "success": True,
            "position_id": position.id,
            "entry_price": current_price,
            "fee": fee
        }
    
    def close_position(self, position_id: str, ratio: float, current_price: float) -> Dict:
        if position_id not in self.positions:
            return {"success": False, "error": f"仓位不存在: {position_id}"}
        
        if ratio <= 0 or ratio > 1:
            return {"success": False, "error": f"平仓比例必须在 (0, 1] 范围内: {ratio}"}
        
        position = self.positions[position_id]
        if position.status == PositionStatus.CLOSED:
            return {"success": False, "error": "仓位已关闭"}
        
        close_amount = position.amount * ratio
        fee = close_amount * self.fee_rate
        
        if position.direction == Direction.LONG:
            pnl = (current_price - position.entry_price) * close_amount / position.entry_price
        else:
            pnl = (position.entry_price - current_price) * close_amount / position.entry_price
        
        realized_pnl = pnl - fee
        self.total_balance += realized_pnl
        
        if ratio >= 0.9999:
            position.status = PositionStatus.CLOSED
            position.close_time = datetime.now()
            position.close_price = current_price
            position.realized_pnl = realized_pnl
        else:
            position.amount *= (1 - ratio)
        
        self.trade_history.append({
            "timestamp": datetime.now(),
            "type": "close_position",
            "position_id": position_id,
            "close_price": current_price,
            "ratio": ratio,
            "realized_pnl": realized_pnl,
            "fee": fee
        })
        
        self._trigger_state_change()
        
        return {
            "success": True,
            "closed_amount": close_amount,
            "realized_pnl": realized_pnl,
            "fee": fee
        }
    
    def modify_position(self, position_id: str, stop_loss: Optional[float] = None,
                       take_profit: Optional[float] = None) -> Dict:
        if position_id not in self.positions:
            return {"success": False, "error": f"仓位不存在: {position_id}"}
        
        position = self.positions[position_id]
        
        if stop_loss is not None:
            position.stop_loss = stop_loss
        if take_profit is not None:
            position.take_profit = take_profit
        
        self._trigger_state_change()
        
        return {"success": True, "message": "仓位已更新"}
    
    def create_plan(self, symbol: str, trigger_price: float, direction: str, amount: float,
                   leverage: int, stop_loss: float, take_profit: float) -> Dict:
        try:
            dir_enum = Direction(direction)
        except ValueError:
            return {"success": False, "error": f"无效的方向: {direction}"}
        
        valid, msg = self.validate_position(amount, leverage, stop_loss, trigger_price, dir_enum)
        if not valid:
            return {"success": False, "error": msg}
        
        plan = TradingPlan(
            id=f"plan_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            trigger_price=trigger_price,
            direction=dir_enum,
            amount=amount,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            create_time=datetime.now()
        )
        
        self.plans[plan.id] = plan
        
        self._trigger_state_change()
        
        return {"success": True, "plan_id": plan.id}
    
    def modify_plan(self, plan_id: str, **kwargs) -> Dict:
        if plan_id not in self.plans:
            return {"success": False, "error": f"计划不存在: {plan_id}"}
        
        plan = self.plans[plan_id]
        if plan.status != PlanStatus.PENDING:
            return {"success": False, "error": "只能修改待触发的计划"}
        
        for key, value in kwargs.items():
            if hasattr(plan, key) and value is not None:
                setattr(plan, key, value)
        
        self._trigger_state_change()
        
        return {"success": True, "message": "计划已更新"}
    
    def cancel_plan(self, plan_id: str) -> Dict:
        if plan_id not in self.plans:
            return {"success": False, "error": f"计划不存在: {plan_id}"}
        
        plan = self.plans[plan_id]
        plan.status = PlanStatus.CANCELLED
        
        self._trigger_state_change()
        
        return {"success": True, "message": "计划已取消"}
    
    def get_positions(self) -> List[Dict]:
        result = []
        for pos in self.positions.values():
            if pos.status == PositionStatus.OPEN:
                unrealized_pnl = pos.unrealized_pnl(self.last_price) if self.last_price else 0
                pnl_percent = (unrealized_pnl / pos.amount) * 100 if pos.amount > 0 else 0
                hold_time = (datetime.now() - pos.open_time).total_seconds()
                
                result.append({
                    "position_id": pos.id,
                    "symbol": pos.symbol,
                    "direction": pos.direction.value,
                    "entry_price": pos.entry_price,
                    "current_price": self.last_price,
                    "amount": pos.amount,
                    "leverage": pos.leverage,
                    "unrealized_pnl": unrealized_pnl,
                    "pnl_percent": pnl_percent,
                    "stop_loss": pos.stop_loss,
                    "take_profit": pos.take_profit,
                    "hold_time_seconds": hold_time
                })
        return result
    
    def get_plans(self) -> List[Dict]:
        result = []
        for plan in self.plans.values():
            if plan.status == PlanStatus.PENDING:
                result.append({
                    "plan_id": plan.id,
                    "symbol": plan.symbol,
                    "trigger_price": plan.trigger_price,
                    "direction": plan.direction.value,
                    "amount": plan.amount,
                    "leverage": plan.leverage,
                    "stop_loss": plan.stop_loss,
                    "take_profit": plan.take_profit,
                    "create_time": plan.create_time.isoformat()
                })
        return result
    
    def check_and_trigger_plans(self, current_price: float):
        triggered_plans = []
        
        if self.last_price is None:
            self.last_price = current_price
            return triggered_plans
        
        for plan in list(self.plans.values()):
            if plan.check_trigger(current_price, self.last_price):
                result = self.open_position(
                    symbol=plan.symbol,
                    direction=plan.direction.value,
                    amount=plan.amount,
                    leverage=plan.leverage,
                    stop_loss=plan.stop_loss,
                    take_profit=plan.take_profit,
                    current_price=current_price
                )
                
                plan.status = PlanStatus.TRIGGERED
                triggered_plans.append({
                    "plan_id": plan.id,
                    "result": result
                })
        
        return triggered_plans
    
    def check_stop_loss_take_profit(self, current_price: float):
        auto_closed = []
        
        for pos in list(self.positions.values()):
            if pos.status == PositionStatus.OPEN:
                trigger = pos.check_stop_loss_take_profit(current_price)
                if trigger:
                    result = self.close_position(pos.id, 1.0, current_price)
                    auto_closed.append({
                        "position_id": pos.id,
                        "trigger": trigger,
                        "result": result
                    })
        
        return auto_closed
    
    def update_price(self, current_price: float):
        triggered = self.check_and_trigger_plans(current_price)
        closed = self.check_stop_loss_take_profit(current_price)
        self.last_price = current_price
        
        return {
            "triggered_plans": triggered,
            "auto_closed_positions": closed
        }