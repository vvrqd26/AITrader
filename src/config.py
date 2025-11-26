import json
import os
from typing import Dict, Any

class Config:
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def load_system_prompt(self) -> str:
        """加载system prompt，支持从文件或配置中读取，并替换动态配置项"""
        prompt_file = "prompts/system_prompt.md"
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = self.get('agent.system_prompt', '')
        
        content = content.replace('{max_position_ratio}', str(int(self.max_position_ratio * 100)))
        content = content.replace('{max_leverage}', str(self.max_leverage))
        content = content.replace('{min_stop_loss_percent}', str(int(self.min_stop_loss_percent * 100)))
        
        return content
    
    @property
    def deepseek_key(self) -> str:
        return self.get('api_keys.deepseek', '')
    
    @property
    def gateio_key(self) -> str:
        return self.get('api_keys.gateio_key', '')
    
    @property
    def gateio_secret(self) -> str:
        return self.get('api_keys.gateio_secret', '')
    
    @property
    def symbol(self) -> str:
        return self.get('trading.symbol', 'BTC_USDT')
    
    @property
    def initial_balance(self) -> float:
        return float(self.get('trading.initial_balance', 100000))
    
    @property
    def fee_rate(self) -> float:
        return float(self.get('trading.fee_rate', 0.0001))
    
    @property
    def max_position_ratio(self) -> float:
        return float(self.get('trading.max_position_ratio', 0.3))
    
    @property
    def max_leverage(self) -> int:
        return int(self.get('trading.max_leverage', 20))
    
    @property
    def min_stop_loss_percent(self) -> float:
        return float(self.get('trading.min_stop_loss_percent', 0.05))
    
    @property
    def timeframes(self) -> list:
        return self.get('indicators.timeframes', ['15m', '1h', '4h', '1d', '1w'])
    
    @property
    def indicator_types(self) -> list:
        return self.get('indicators.types', ['MA', 'EMA', 'MACD', 'RSI'])
    
    @property
    def loop_interval(self) -> int:
        return int(self.get('loop.interval', 60))
    
    @property
    def plan_check_interval(self) -> int:
        return int(self.get('loop.plan_check_interval', 1))
    
    @property
    def system_prompt(self) -> str:
        return self.load_system_prompt()

config = Config()