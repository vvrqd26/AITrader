#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.persistence import StatePersistence

def main():
    persistence = StatePersistence()
    state = persistence.load_state()
    
    if not state:
        print("未找到保存的状态")
        return
    
    print("=" * 60)
    print("保存的状态信息")
    print("=" * 60)
    print(f"\n保存时间: {state.get('timestamp', 'N/A')}")
    print(f"循环周期: {state.get('cycle_count', 0)}")
    
    executor_state = state.get('executor', {})
    print(f"\n账户余额: ${executor_state.get('total_balance', 0):.2f}")
    print(f"最后价格: ${executor_state.get('last_price', 0):.2f}")
    
    positions = executor_state.get('positions', {})
    print(f"\n持仓数量: {len(positions)}")
    if positions:
        for pos_id, pos in positions.items():
            print(f"  [{pos_id}] {pos['direction'].upper()} "
                  f"${pos['amount']:.2f} @ {pos['leverage']}x "
                  f"(入场: ${pos['entry_price']:.2f})")
    
    plans = executor_state.get('plans', {})
    print(f"\n计划数量: {len(plans)}")
    if plans:
        for plan_id, plan in plans.items():
            print(f"  [{plan_id}] 触发价${plan['trigger_price']:.2f} "
                  f"{plan['direction'].upper()} ${plan['amount']:.2f}")
    
    trade_history = executor_state.get('trade_history', [])
    print(f"\n历史交易: {len(trade_history)} 笔")
    
    print("\n" + "=" * 60)
    
    choice = input("\n是否删除保存的状态? (y/N): ").strip().lower()
    if choice == 'y':
        import json
        state_file = persistence.state_file
        if os.path.exists(state_file):
            os.remove(state_file)
            print(f"已删除状态文件: {state_file}")
        else:
            print("状态文件不存在")

if __name__ == "__main__":
    main()
