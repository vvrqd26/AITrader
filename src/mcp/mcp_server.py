import json
import sys
from typing import Any, Dict, List
from datetime import datetime

class MCPServer:
    def __init__(self, executor, alert_manager=None):
        self.executor = executor
        self.alert_manager = alert_manager
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict]:
        return [
            {
                "name": "open_position",
                "description": "开仓操作，创建新的多头或空头仓位",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "交易对，如BTC/USDT"},
                        "direction": {"type": "string", "enum": ["long", "short"], "description": "方向：long做多，short做空"},
                        "amount": {"type": "number", "description": "开仓金额（USD）"},
                        "leverage": {"type": "integer", "description": "杠杆倍数"},
                        "stop_loss": {"type": "number", "description": "止损价格"},
                        "take_profit": {"type": "number", "description": "止盈价格"}
                    },
                    "required": ["symbol", "direction", "amount", "leverage", "stop_loss", "take_profit"]
                }
            },
            {
                "name": "close_position",
                "description": "平仓操作，关闭已有仓位",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "position_id": {"type": "string", "description": "仓位ID"},
                        "ratio": {"type": "number", "description": "平仓比例，0-1之间，1表示全部平仓", "default": 1.0}
                    },
                    "required": ["position_id"]
                }
            },
            {
                "name": "modify_position",
                "description": "修改仓位的止损止盈价格",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "position_id": {"type": "string", "description": "仓位ID"},
                        "stop_loss": {"type": "number", "description": "新的止损价格"},
                        "take_profit": {"type": "number", "description": "新的止盈价格"}
                    },
                    "required": ["position_id"]
                }
            },
            {
                "name": "create_plan",
                "description": "创建交易计划，当价格达到触发价时自动开仓",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "交易对"},
                        "trigger_price": {"type": "number", "description": "触发价格"},
                        "direction": {"type": "string", "enum": ["long", "short"], "description": "方向"},
                        "amount": {"type": "number", "description": "开仓金额"},
                        "leverage": {"type": "integer", "description": "杠杆倍数"},
                        "stop_loss": {"type": "number", "description": "止损价格"},
                        "take_profit": {"type": "number", "description": "止盈价格"}
                    },
                    "required": ["symbol", "trigger_price", "direction", "amount", "leverage", "stop_loss", "take_profit"]
                }
            },
            {
                "name": "modify_plan",
                "description": "修改交易计划",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan_id": {"type": "string", "description": "计划ID"},
                        "trigger_price": {"type": "number", "description": "触发价格"},
                        "amount": {"type": "number", "description": "开仓金额"},
                        "leverage": {"type": "integer", "description": "杠杆倍数"},
                        "stop_loss": {"type": "number", "description": "止损价格"},
                        "take_profit": {"type": "number", "description": "止盈价格"}
                    },
                    "required": ["plan_id"]
                }
            },
            {
                "name": "cancel_plan",
                "description": "取消交易计划",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan_id": {"type": "string", "description": "计划ID"}
                    },
                    "required": ["plan_id"]
                }
            },
            {
                "name": "get_account_info",
                "description": "获取账户信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_positions",
                "description": "获取所有持仓",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_plans",
                "description": "获取所有待触发的交易计划",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "set_price_alert",
                "description": "设置价格预警，当价格突破指定价位时立即触发AI决策。用于捕捉突破、回调等关键时机",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number", "description": "预警价格"},
                        "condition": {
                            "type": "string", 
                            "enum": ["above", "below"],
                            "description": "触发条件：above=价格上穿时触发，below=价格下穿时触发"
                        },
                        "description": {"type": "string", "description": "预警说明，如'突破2950阻力位'"}
                    },
                    "required": ["price", "condition"]
                }
            },
            {
                "name": "cancel_price_alert",
                "description": "取消价格预警",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "alert_id": {"type": "string", "description": "预警ID"}
                    },
                    "required": ["alert_id"]
                }
            },
            {
                "name": "get_price_alerts",
                "description": "获取所有活跃的价格预警",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        try:
            if tool_name == "open_position":
                if 'current_price' not in arguments:
                    return {"success": False, "error": "缺少current_price参数"}
                return self.executor.open_position(**arguments)
            
            elif tool_name == "close_position":
                if 'current_price' not in arguments:
                    return {"success": False, "error": "缺少current_price参数"}
                arguments.setdefault('ratio', 1.0)
                return self.executor.close_position(**arguments)
            
            elif tool_name == "modify_position":
                return self.executor.modify_position(**arguments)
            
            elif tool_name == "create_plan":
                return self.executor.create_plan(**arguments)
            
            elif tool_name == "modify_plan":
                return self.executor.modify_plan(**arguments)
            
            elif tool_name == "cancel_plan":
                return self.executor.cancel_plan(**arguments)
            
            elif tool_name == "get_account_info":
                account = self.executor.get_account_info()
                return {
                    "success": True,
                    "data": {
                        "total_balance": account.total_balance,
                        "available": account.available,
                        "margin_used": account.margin_used,
                        "unrealized_pnl": account.unrealized_pnl,
                        "equity": account.equity
                    }
                }
            
            elif tool_name == "get_positions":
                return {"success": True, "data": self.executor.get_positions()}
            
            elif tool_name == "get_plans":
                return {"success": True, "data": self.executor.get_plans()}
            
            elif tool_name == "set_price_alert":
                if not self.alert_manager:
                    return {"success": False, "error": "价格预警功能未启用"}
                
                # 这里的callback会在主程序中设置
                # 暂时返回成功，实际触发在price_stream中处理
                return {
                    "success": True, 
                    "message": f"价格预警已设置: {arguments.get('condition')} ${arguments.get('price')}",
                    "alert_data": arguments
                }
            
            elif tool_name == "cancel_price_alert":
                if not self.alert_manager:
                    return {"success": False, "error": "价格预警功能未启用"}
                
                success = self.alert_manager.cancel_alert(arguments['alert_id'])
                return {
                    "success": success,
                    "message": "预警已取消" if success else "预警不存在"
                }
            
            elif tool_name == "get_price_alerts":
                if not self.alert_manager:
                    return {"success": True, "data": []}
                
                return {"success": True, "data": self.alert_manager.get_active_alerts()}
            
            else:
                return {"success": False, "error": f"未知工具: {tool_name}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_tools_description(self) -> str:
        description = "可用的交易工具：\n\n"
        for tool in self.tools:
            description += f"【{tool['name']}】\n"
            description += f"{tool['description']}\n"
            description += f"参数: {json.dumps(tool['inputSchema']['properties'], ensure_ascii=False, indent=2)}\n\n"
        return description
    
    def format_tool_calls_for_llm(self) -> List[Dict]:
        """格式化工具定义为OpenAI function calling格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"]
                }
            }
            for tool in self.tools
        ]