from openai import OpenAI
import json
from typing import Dict, List, Optional
from datetime import datetime

class TradingAgent:
    def __init__(self, api_key: str, system_prompt: str, model: str = "deepseek-chat"):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = model
        self.system_prompt = system_prompt
        self.conversation_history = []
    
    def make_decision(self, market_info: str, tools: List[Dict], current_price: float, 
                     execution_feedback: Optional[str] = None) -> Dict:
        """
        让Agent做出交易决策
        
        Args:
            market_info: 格式化的市场信息字符串
            tools: 可用工具列表（OpenAI function calling格式）
            current_price: 当前价格（用于工具调用）
            execution_feedback: 上次执行的反馈（如果有错误）
        
        Returns:
            {
                "analysis": "市场分析文本",
                "tool_calls": [{"name": "tool_name", "arguments": {...}}],
                "raw_response": "原始响应"
            }
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            if len(self.conversation_history) > 0:
                messages.extend(self.conversation_history[-6:])
            
            user_message = market_info
            if execution_feedback:
                user_message += f"\n\n【上次操作反馈】\n{execution_feedback}"
            
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7
            )
            
            message = response.choices[0].message
            
            result = {
                "analysis": message.content or "",
                "tool_calls": [],
                "raw_response": message.model_dump()
            }
            
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                        
                        if tool_call.function.name in ["open_position", "close_position"]:
                            arguments["current_price"] = current_price
                        
                        result["tool_calls"].append({
                            "id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": arguments
                        })
                    except json.JSONDecodeError as e:
                        result["tool_calls"].append({
                            "error": f"解析工具参数失败: {e}",
                            "raw_arguments": tool_call.function.arguments
                        })
            
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": message.content or ""})
            
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return result
        
        except Exception as e:
            return {
                "analysis": "",
                "tool_calls": [],
                "error": str(e),
                "raw_response": None
            }
    
    def add_to_history(self, role: str, content: str):
        """添加到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history[-limit:]
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []