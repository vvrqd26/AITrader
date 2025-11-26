import json
import os
from datetime import datetime
from typing import Dict, Any
import logging
from logging.handlers import RotatingFileHandler

class Logger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        self.decision_log_file = os.path.join(log_dir, "decision.log")
        self.trade_log_file = os.path.join(log_dir, "trades.log")
        self.system_log_file = os.path.join(log_dir, "system.log")
        
        self._setup_system_logger()
    
    def _setup_system_logger(self):
        """设置系统日志记录器"""
        self.system_logger = logging.getLogger("system")
        self.system_logger.setLevel(logging.DEBUG)
        
        handler = RotatingFileHandler(
            self.system_log_file,
            maxBytes=100*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        
        console_handler = logging.StreamHandler()
        
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.system_logger.addHandler(handler)
        self.system_logger.addHandler(console_handler)
    
    def log_decision(self, cycle: int, input_data: Dict, agent_output: Dict, 
                    execution_results: list, duration_ms: float):
        """记录决策日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "cycle": cycle,
            "input": input_data,
            "agent_output": agent_output,
            "execution": execution_results,
            "duration_ms": duration_ms
        }
        
        with open(self.decision_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_trade(self, trade_type: str, params: Dict, result: Dict):
        """记录交易日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": trade_type,
            "params": params,
            "result": result
        }
        
        with open(self.trade_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def info(self, message: str):
        """记录INFO级别日志"""
        self.system_logger.info(message)
    
    def warning(self, message: str):
        """记录WARNING级别日志"""
        self.system_logger.warning(message)
    
    def error(self, message: str):
        """记录ERROR级别日志"""
        self.system_logger.error(message)
    
    def debug(self, message: str):
        """记录DEBUG级别日志"""
        self.system_logger.debug(message)
