#!/usr/bin/env python3

import asyncio
import time
import threading
from datetime import datetime

from src.config import config
from src.executor import SimulatedExecutor
from src.collector import MarketDataCollector, PriceStreamManager
from src.mcp import MCPServer
from src.agent import TradingAgent
from src.logger import Logger
from src.web import WebPanel
from src.persistence import StatePersistence

import uvicorn

class AITrader:
    def __init__(self):
        self.config = config
        self.logger = Logger()
        
        self.logger.info("初始化 AI Trader...")
        
        self.executor = SimulatedExecutor(
            initial_balance=self.config.initial_balance,
            fee_rate=self.config.fee_rate,
            max_position_ratio=self.config.max_position_ratio,
            max_leverage=self.config.max_leverage,
            min_stop_loss_percent=self.config.min_stop_loss_percent
        )
        
        self.executor.on_state_change = self.save_state_callback
        
        self.persistence = StatePersistence()
        
        saved_state = self.persistence.load_state()
        if saved_state:
            self.logger.info("发现保存的状态，正在恢复...")
            self.cycle_count = self.persistence.restore_executor(self.executor, saved_state)
            self.logger.info(f"状态已恢复，将从周期 {self.cycle_count + 1} 继续")
        else:
            self.logger.info("未发现保存的状态，从头开始")
            self.cycle_count = 0
        
        self.collector = MarketDataCollector(self.config)
        
        self.price_stream = PriceStreamManager(
            symbol=self.config.symbol,
            callback=self.on_price_update
        )
        
        self.mcp_server = MCPServer(self.executor)
        
        self.agent = TradingAgent(
            api_key=self.config.deepseek_key,
            system_prompt=self.config.system_prompt
        )
        
        self.web_panel = WebPanel()
        self.web_panel.set_executor(self.executor)
        
        self.running = False
        self.price_stream_task = None
        
        self.logger.info("AI Trader 初始化完成")
    
    def save_state_callback(self):
        """状态变化时自动保存"""
        try:
            self.persistence.save_state(self.executor, self.cycle_count)
        except Exception as e:
            self.logger.error(f"自动保存状态失败: {e}")
    
    def on_price_update(self, price: float):
        """价格更新回调"""
        try:
            result = self.executor.update_price(price)
            
            if result['triggered_plans']:
                self.logger.info(f"[实时] 触发 {len(result['triggered_plans'])} 个交易计划 @ ${price:.2f}")
                for triggered in result['triggered_plans']:
                    self.logger.log_trade(
                        "triggered_plan",
                        {"plan_id": triggered['plan_id'], "trigger_price": price},
                        triggered['result']
                    )
            
            if result['auto_closed_positions']:
                self.logger.info(f"[实时] 自动平仓 {len(result['auto_closed_positions'])} 个仓位 @ ${price:.2f}")
                for closed in result['auto_closed_positions']:
                    self.logger.log_trade(
                        f"auto_close_{closed['trigger']}",
                        {"position_id": closed['position_id'], "close_price": price},
                        closed['result']
                    )
        except Exception as e:
            self.logger.error(f"价格更新回调错误: {e}")
    
    def start_plan_monitor(self):
        """启动交易计划监控线程 (已被实时价格推送取代)"""
        pass
    
    async def main_loop(self):
        """主决策循环"""
        self.logger.info("主循环启动")
        self.running = True
        
        self.price_stream_task = asyncio.create_task(self.price_stream.start())
        self.logger.info("实时价格推送已启动")
        
        await asyncio.sleep(2)
        
        while self.running:
            try:
                self.cycle_count += 1
                cycle_start = time.time()
                
                self.logger.info(f"===== 周期 {self.cycle_count} =====")
                
                self.web_panel.update_system_status(
                    status="running",
                    cycle=self.cycle_count,
                    last_decision_time=datetime.now().isoformat()
                )
                
                market_data = self.collector.collect_market_data(
                    self.config.symbol.replace('_', '/')
                )
                
                if "error" in market_data:
                    self.logger.error(f"获取市场数据失败: {market_data['error']}")
                    await asyncio.sleep(self.config.loop_interval)
                    continue
                
                current_price = market_data.get('current_price')
                if not current_price:
                    self.logger.error("无法获取当前价格")
                    await asyncio.sleep(self.config.loop_interval)
                    continue
                
                account_info_obj = self.executor.get_account_info()
                account_info = {
                    "total_balance": account_info_obj.total_balance,
                    "available": account_info_obj.available,
                    "margin_used": account_info_obj.margin_used,
                    "unrealized_pnl": account_info_obj.unrealized_pnl,
                    "equity": account_info_obj.equity
                }
                
                positions = self.executor.get_positions()
                plans = self.executor.get_plans()
                
                self.web_panel.update_account(account_info)
                self.web_panel.update_positions(positions)
                self.web_panel.update_plans(plans)
                
                formatted_info = self.collector.format_data_for_agent(
                    market_data, account_info, positions, plans
                )
                
                self.logger.debug(f"市场信息:\n{formatted_info}")
                
                tools = self.mcp_server.format_tool_calls_for_llm()
                
                execution_feedback = None
                max_retries = 2
                
                for retry in range(max_retries):
                    decision = self.agent.make_decision(formatted_info, tools, current_price, execution_feedback)
                    
                    if "error" in decision:
                        self.logger.error(f"Agent决策失败: {decision['error']}")
                        await asyncio.sleep(self.config.loop_interval)
                        continue
                    
                    self.logger.info(f"Agent分析: {decision['analysis']}")
                    
                    execution_results = []
                    has_error = False
                    
                    if decision['tool_calls']:
                        self.logger.info(f"执行 {len(decision['tool_calls'])} 个工具调用")
                        
                        for tool_call in decision['tool_calls']:
                            if 'error' in tool_call:
                                self.logger.error(f"工具调用错误: {tool_call['error']}")
                                execution_results.append(tool_call)
                                continue
                            
                            result = self.mcp_server.handle_tool_call(
                                tool_call['name'],
                                tool_call['arguments']
                            )
                            
                            self.logger.info(f"工具 {tool_call['name']} 结果: {result}")
                            self.logger.log_trade(
                                tool_call['name'],
                                tool_call['arguments'],
                                result
                            )
                            
                            execution_results.append({
                                "tool": tool_call['name'],
                                "arguments": tool_call['arguments'],
                                "result": result
                            })
                            
                            if not result.get('success', False):
                                has_error = True
                        
                        if has_error and retry < max_retries - 1:
                            error_messages = []
                            for exec_result in execution_results:
                                if 'result' in exec_result and not exec_result['result'].get('success', False):
                                    error_msg = exec_result['result'].get('error', '未知错误')
                                    tool_name = exec_result['tool']
                                    error_messages.append(f"- {tool_name}: {error_msg}")
                            
                            execution_feedback = "上次操作失败，请根据以下错误调整策略:\n" + "\n".join(error_messages)
                            self.logger.warning(f"工具执行失败，准备重试 ({retry + 1}/{max_retries - 1})")
                            self.logger.warning(execution_feedback)
                            
                            await asyncio.sleep(2)
                            continue
                        else:
                            break
                    else:
                        self.logger.info("无需执行交易")
                        break
                
                self.web_panel.add_decision({
                    "analysis": decision['analysis'],
                    "tool_calls": decision['tool_calls'],
                    "execution_results": execution_results
                })
                
                cycle_duration = (time.time() - cycle_start) * 1000
                
                self.logger.log_decision(
                    cycle=self.cycle_count,
                    input_data={
                        "market_data": market_data,
                        "account_info": account_info,
                        "positions": positions,
                        "plans": plans
                    },
                    agent_output=decision,
                    execution_results=execution_results,
                    duration_ms=cycle_duration
                )
                
                self.logger.info(f"周期 {self.cycle_count} 完成，耗时 {cycle_duration:.2f}ms")
                
                last_price = self.price_stream.get_last_price()
                update_age = self.price_stream.get_update_age()
                if last_price:
                    self.logger.debug(f"实时价格: ${last_price:.2f} (更新于 {update_age:.1f}秒前)")
                
                if self.cycle_count % 10 == 0:
                    self.persistence.save_state(self.executor, self.cycle_count)
                    self.logger.info(f"状态已保存 (周期 {self.cycle_count})")
                
                await asyncio.sleep(self.config.loop_interval)
            
            except KeyboardInterrupt:
                self.logger.info("接收到停止信号")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"主循环错误: {e}", exc_info=True)
                await asyncio.sleep(self.config.loop_interval)
        
        self.logger.info("主循环已退出")
    
    def start(self):
        """启动交易系统"""
        try:
            self.logger.info("启动 AI Trader 系统")
            
            async def run_app():
                web_config = uvicorn.Config(
                    self.web_panel.app,
                    host="0.0.0.0",
                    port=8000,
                    log_level="error"
                )
                server = uvicorn.Server(web_config)
                
                async def shutdown_handler():
                    """优雅关闭处理"""
                    self.logger.info("收到关闭信号，正在停止系统...")
                    self.running = False
                    
                    self.logger.info("停止价格推送...")
                    self.price_stream.stop()
                    if self.price_stream_task and not self.price_stream_task.done():
                        self.price_stream_task.cancel()
                        try:
                            await self.price_stream_task
                        except asyncio.CancelledError:
                            pass
                    
                    self.logger.info("保存最终状态...")
                    self.persistence.save_state(self.executor, self.cycle_count)
                    
                    self.logger.info("停止Web服务器...")
                    await server.shutdown()
                
                server.install_signal_handlers = lambda: None
                
                main_task = asyncio.create_task(self.main_loop())
                server_task = asyncio.create_task(server.serve())
                
                try:
                    await asyncio.gather(server_task, main_task)
                except KeyboardInterrupt:
                    self.logger.info("检测到 Ctrl+C")
                    await shutdown_handler()
                except asyncio.CancelledError:
                    self.logger.info("任务被取消")
                    await shutdown_handler()
            
            asyncio.run(run_app())
        
        except KeyboardInterrupt:
            self.logger.info("系统已停止")
        except Exception as e:
            self.logger.error(f"系统错误: {e}", exc_info=True)

def main():
    trader = AITrader()
    trader.start()

if __name__ == "__main__":
    main()