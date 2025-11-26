from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class PriceAlert:
    id: str
    price: float
    condition: str  # 'above' or 'below'
    callback: Callable
    create_time: datetime
    triggered: bool = False
    description: str = ""

class PriceAlertManager:
    """价格预警管理器 - 触发AI立即决策"""
    
    def __init__(self):
        self.alerts: Dict[str, PriceAlert] = {}
        self.last_price: Optional[float] = None
    
    def create_alert(self, price: float, condition: str, callback: Callable, 
                    description: str = "") -> str:
        """
        创建价格预警（自动去重）
        
        Args:
            price: 触发价格
            condition: 'above' 价格上穿时触发, 'below' 价格下穿时触发
            callback: 触发时的回调函数
            description: 预警描述
        
        Returns:
            alert_id
        """
        # 检查是否已存在相同的预警
        for alert in self.alerts.values():
            if abs(alert.price - price) < 0.01 and alert.condition == condition:
                # 相同价格和方向的预警已存在，不重复创建
                return alert.id
        
        import uuid
        alert_id = f"alert_{uuid.uuid4().hex[:8]}"
        
        alert = PriceAlert(
            id=alert_id,
            price=price,
            condition=condition,
            callback=callback,
            create_time=datetime.now(),
            description=description
        )
        
        self.alerts[alert_id] = alert
        return alert_id
    
    def cancel_alert(self, alert_id: str) -> bool:
        """取消预警"""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            return True
        return False
    
    def check_alerts(self, current_price: float):
        """检查价格预警"""
        if self.last_price is None:
            self.last_price = current_price
            return
        
        triggered_alerts = []
        
        for alert_id, alert in list(self.alerts.items()):
            if alert.triggered:
                continue
            
            triggered = False
            
            if alert.condition == 'above':
                # 向上突破
                if self.last_price < alert.price <= current_price:
                    triggered = True
            elif alert.condition == 'below':
                # 向下突破
                if self.last_price > alert.price >= current_price:
                    triggered = True
            
            if triggered:
                alert.triggered = True
                triggered_alerts.append(alert)
                
                try:
                    alert.callback(alert, current_price)
                except Exception as e:
                    print(f"价格预警回调错误: {e}")
                
                # 预警是一次性的，触发后删除
                del self.alerts[alert_id]
        
        self.last_price = current_price
        return triggered_alerts
    
    def get_active_alerts(self) -> List[Dict]:
        """获取活跃的预警"""
        return [
            {
                "alert_id": alert.id,
                "price": alert.price,
                "condition": alert.condition,
                "description": alert.description,
                "create_time": alert.create_time.isoformat()
            }
            for alert in self.alerts.values()
            if not alert.triggered
        ]
    
    def to_dict(self) -> Dict:
        """序列化为字典（用于持久化）"""
        return {
            "alerts": [
                {
                    "id": alert.id,
                    "price": alert.price,
                    "condition": alert.condition,
                    "description": alert.description,
                    "create_time": alert.create_time.isoformat(),
                    "triggered": alert.triggered
                }
                for alert in self.alerts.values()
            ],
            "last_price": self.last_price
        }
    
    def from_dict(self, data: Dict, callback: Callable):
        """从字典恢复（用于持久化）"""
        self.last_price = data.get('last_price')
        
        for alert_data in data.get('alerts', []):
            if not alert_data.get('triggered', False):
                alert = PriceAlert(
                    id=alert_data['id'],
                    price=alert_data['price'],
                    condition=alert_data['condition'],
                    callback=callback,
                    create_time=datetime.fromisoformat(alert_data['create_time']),
                    triggered=alert_data.get('triggered', False),
                    description=alert_data.get('description', '')
                )
                self.alerts[alert.id] = alert