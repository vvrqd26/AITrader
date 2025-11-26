import asyncio
import json
from typing import Callable, Optional
import websockets
from datetime import datetime

class PriceStreamManager:
    """实时价格推送管理器 - 使用WebSocket"""
    
    def __init__(self, symbol: str, callback: Callable[[float], None]):
        """
        Args:
            symbol: 交易对，如 BTC_USDT
            callback: 价格更新回调函数
        """
        self.symbol = symbol
        self.callback = callback
        self.running = False
        self.websocket = None
        
        self.ws_url = "wss://ws.gate.io/v4/ws/usdt"
        
        self.last_price = None
        self.last_update_time = None
    
    async def start(self):
        """启动WebSocket连接"""
        self.running = True
        
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.websocket = ws
                    
                    subscribe_msg = {
                        "time": int(datetime.now().timestamp()),
                        "channel": "futures.tickers",
                        "event": "subscribe",
                        "payload": [self.symbol]
                    }
                    
                    await ws.send(json.dumps(subscribe_msg))
                    print(f"已订阅 {self.symbol} 实时价格推送")
                    
                    async for message in ws:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            
                            if data.get('event') == 'update' and data.get('channel') == 'futures.tickers':
                                result = data.get('result')
                                if result and isinstance(result, dict):
                                    if result.get('contract') == self.symbol:
                                        price = float(result.get('last', 0))
                                        
                                        if price > 0:
                                            self.last_price = price
                                            self.last_update_time = datetime.now()
                                            
                                            await asyncio.to_thread(self.callback, price)
                        
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print(f"处理WebSocket消息错误: {e}")
            
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket连接断开，3秒后重连...")
                await asyncio.sleep(3)
            except Exception as e:
                print(f"WebSocket连接错误: {e}, 5秒后重试...")
                await asyncio.sleep(5)
    
    def stop(self):
        """停止WebSocket连接"""
        self.running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())
    
    def get_last_price(self) -> Optional[float]:
        """获取最后接收的价格"""
        return self.last_price
    
    def get_update_age(self) -> Optional[float]:
        """获取价格更新时间差（秒）"""
        if self.last_update_time:
            return (datetime.now() - self.last_update_time).total_seconds()
        return None
