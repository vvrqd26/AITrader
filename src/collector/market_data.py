import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
import time

class DataCollector:
    def __init__(self, exchange_id: str = 'gate', api_key: str = '', api_secret: str = '',
                 cache_dir: str = 'data/cache', cache_ttl: int = 86400):
        exchange_config = {
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        }
        
        if api_key and api_secret:
            exchange_config['apiKey'] = api_key
            exchange_config['secret'] = api_secret
        
        self.exchange = getattr(ccxt, exchange_id)(exchange_config)
        
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            print(f"获取当前价格失败: {e}")
            return None
    
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[pd.DataFrame]:
        cache_file = os.path.join(self.cache_dir, f"{symbol.replace('/', '_')}_{timeframe}.json")
        
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            if len(df) < limit * 0.8:
                print(f"警告: {symbol} {timeframe} 只获取到 {len(df)}/{limit} 条数据")
            
            cache_data = df.to_dict('records')
            for item in cache_data:
                item['timestamp'] = item['timestamp'].isoformat()
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            print(f"获取K线数据失败 {symbol} {timeframe}: {e}")
            
            if os.path.exists(cache_file):
                try:
                    print(f"尝试使用缓存数据 {cache_file}")
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        df = pd.DataFrame(data)
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        print(f"从缓存加载 {len(df)} 条数据")
                        return df
                except Exception as cache_error:
                    print(f"读取缓存失败: {cache_error}")
            
            return None

class IndicatorCalculator:
    @staticmethod
    def calculate_ma(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        for period in periods:
            df[f'MA{period}'] = df['close'].rolling(window=period).mean()
        return df
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        for period in periods:
            df[f'EMA{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        return df
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        return df
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df
    
    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std: int = 2) -> pd.DataFrame:
        df['BOLL_middle'] = df['close'].rolling(window=period).mean()
        rolling_std = df['close'].rolling(window=period).std()
        df['BOLL_upper'] = df['BOLL_middle'] + (rolling_std * std)
        df['BOLL_lower'] = df['BOLL_middle'] - (rolling_std * std)
        return df
    
    @staticmethod
    def calculate_kdj(df: pd.DataFrame, period: int = 9) -> pd.DataFrame:
        low_min = df['low'].rolling(window=period).min()
        high_max = df['high'].rolling(window=period).max()
        
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        df['K'] = rsv.ewm(com=2, adjust=False).mean()
        df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']
        return df
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = true_range.rolling(window=period).mean()
        return df
    
    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        df['OBV'] = obv
        return df
    
    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
        """成交量加权平均价 - 短线交易重要参考"""
        df['VWAP'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        return df
    
    @staticmethod
    def calculate_volume_ma(df: pd.DataFrame, periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """成交量均线 - 判断放量缩量"""
        for period in periods:
            df[f'VOL_MA{period}'] = df['volume'].rolling(window=period).mean()
        
        df['volume_ratio'] = df['volume'] / df['VOL_MA20']
        return df
    
    @staticmethod
    def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """资金流量指数 - 结合价格和成交量的RSI"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        positive_flow = []
        negative_flow = []
        
        for i in range(1, len(df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.append(money_flow.iloc[i])
                negative_flow.append(0)
            elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                positive_flow.append(0)
                negative_flow.append(money_flow.iloc[i])
            else:
                positive_flow.append(0)
                negative_flow.append(0)
        
        positive_flow = pd.Series([0] + positive_flow, index=df.index)
        negative_flow = pd.Series([0] + negative_flow, index=df.index)
        
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()
        
        mfi_ratio = positive_mf / negative_mf
        df['MFI'] = 100 - (100 / (1 + mfi_ratio))
        return df
    
    @staticmethod
    def calculate_atr_percent(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """ATR百分比 - 相对波动率"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = true_range.rolling(window=period).mean()
        df['ATR_percent'] = (df['ATR'] / df['close']) * 100
        return df
    
    @staticmethod
    def calculate_bollinger_bandwidth(df: pd.DataFrame, period: int = 20, std: int = 2) -> pd.DataFrame:
        """布林带宽度 - 判断行情收敛/发散"""
        df['BOLL_middle'] = df['close'].rolling(window=period).mean()
        rolling_std = df['close'].rolling(window=period).std()
        df['BOLL_upper'] = df['BOLL_middle'] + (rolling_std * std)
        df['BOLL_lower'] = df['BOLL_middle'] - (rolling_std * std)
        
        df['BOLL_width'] = ((df['BOLL_upper'] - df['BOLL_lower']) / df['BOLL_middle']) * 100
        df['BOLL_position'] = ((df['close'] - df['BOLL_lower']) / (df['BOLL_upper'] - df['BOLL_lower'])) * 100
        return df
    
    @staticmethod
    def calculate_historical_volatility(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """历史波动率 - 年化波动率"""
        log_return = np.log(df['close'] / df['close'].shift(1))
        df['HV'] = log_return.rolling(window=period).std() * np.sqrt(365) * 100
        return df
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame, ma_periods: List[int] = [5, 10, 20, 60],
                                 rsi_period: int = 14, macd_params: List[int] = [12, 26, 9]) -> pd.DataFrame:
        df = IndicatorCalculator.calculate_ma(df, ma_periods)
        df = IndicatorCalculator.calculate_ema(df, ma_periods)
        df = IndicatorCalculator.calculate_macd(df, *macd_params)
        df = IndicatorCalculator.calculate_rsi(df, rsi_period)
        df = IndicatorCalculator.calculate_bollinger_bandwidth(df)
        df = IndicatorCalculator.calculate_kdj(df)
        df = IndicatorCalculator.calculate_atr_percent(df)
        df = IndicatorCalculator.calculate_obv(df)
        df = IndicatorCalculator.calculate_vwap(df)
        df = IndicatorCalculator.calculate_volume_ma(df, [5, 10, 20])
        df = IndicatorCalculator.calculate_mfi(df)
        df = IndicatorCalculator.calculate_historical_volatility(df)
        return df

class MarketDataCollector:
    def __init__(self, config):
        self.config = config
        self.collector = DataCollector(
            exchange_id='gate',
            api_key=config.gateio_key,
            api_secret=config.gateio_secret,
            cache_ttl=config.get('cache.history_ttl', 86400)
        )
        self.calculator = IndicatorCalculator()
    
    def collect_market_data(self, symbol: str) -> Dict:
        market_data = {
            "symbol": symbol,
            "current_price": None,
            "timestamp": datetime.now().isoformat(),
            "timeframes": {}
        }
        
        for timeframe in self.config.timeframes:
            df = self.collector.get_ohlcv(symbol, timeframe, limit=200)
            
            if df is None or df.empty:
                continue
            
            df = self.calculator.calculate_all_indicators(
                df,
                ma_periods=self.config.get('indicators.ma_periods', [5, 10, 20, 60]),
                rsi_period=self.config.get('indicators.rsi_period', 14),
                macd_params=self.config.get('indicators.macd_params', [12, 26, 9])
            )
            
            latest = df.iloc[-1].to_dict()
            latest['timestamp'] = latest['timestamp'].isoformat() if isinstance(latest['timestamp'], datetime) else latest['timestamp']
            
            prev = df.iloc[-2].to_dict() if len(df) > 1 else {}
            if prev and 'timestamp' in prev:
                prev['timestamp'] = prev['timestamp'].isoformat() if isinstance(prev['timestamp'], datetime) else prev['timestamp']
            
            market_data['timeframes'][timeframe] = {
                "latest": latest,
                "previous": prev,
                "candles_count": len(df)
            }
            
            if timeframe == '1m' and market_data['current_price'] is None:
                market_data['current_price'] = latest.get('close')
        
        if market_data['current_price'] is None:
            return {"error": "无法获取当前价格"}
        
        return market_data
    
    def format_data_for_agent(self, market_data: Dict, account_info: Dict, 
                             positions: List[Dict], plans: List[Dict],
                             alerts: List[Dict] = None) -> str:
        formatted = f"""=== 市场数据 ===
交易对: {market_data.get('symbol', 'N/A')}
当前价格: ${market_data.get('current_price', 0):.2f}
时间: {market_data.get('timestamp', 'N/A')}

"""
        
        for timeframe, data in market_data.get('timeframes', {}).items():
            latest = data.get('latest', {})
            formatted += f"\n【{timeframe}周期】\n"
            formatted += f"  价格: ${latest.get('close', 0):.2f} (高${latest.get('high', 0):.2f}/低${latest.get('low', 0):.2f})\n"
            
            if 'MA5' in latest:
                formatted += f"  MA(5/10/20/60): {latest.get('MA5', 0):.2f}/{latest.get('MA10', 0):.2f}/"
                formatted += f"{latest.get('MA20', 0):.2f}/{latest.get('MA60', 0):.2f}\n"
            
            if 'RSI' in latest:
                formatted += f"  RSI: {latest.get('RSI', 0):.2f}"
                if 'MFI' in latest:
                    formatted += f" | MFI(资金流): {latest.get('MFI', 0):.2f}"
                formatted += "\n"
            
            if 'MACD' in latest:
                formatted += f"  MACD: {latest.get('MACD', 0):.4f} | "
                formatted += f"信号: {latest.get('MACD_signal', 0):.4f} | "
                formatted += f"柱状: {latest.get('MACD_hist', 0):.4f}\n"
            
            if 'BOLL_upper' in latest:
                formatted += f"  BOLL: 上轨{latest.get('BOLL_upper', 0):.2f} | "
                formatted += f"中轨{latest.get('BOLL_middle', 0):.2f} | "
                formatted += f"下轨{latest.get('BOLL_lower', 0):.2f}"
                if 'BOLL_width' in latest:
                    formatted += f" | 带宽{latest.get('BOLL_width', 0):.2f}%"
                if 'BOLL_position' in latest:
                    formatted += f" | 位置{latest.get('BOLL_position', 0):.1f}%"
                formatted += "\n"
            
            volume_info = []
            if 'volume' in latest and 'VOL_MA20' in latest:
                vol_ratio = latest.get('volume_ratio', 0)
                volume_info.append(f"成交量: {latest.get('volume', 0):.0f} (MA20倍数: {vol_ratio:.2f}x)")
            
            if 'VWAP' in latest:
                vwap_diff = ((latest.get('close', 0) - latest.get('VWAP', 0)) / latest.get('VWAP', 1)) * 100
                volume_info.append(f"VWAP: ${latest.get('VWAP', 0):.2f} (偏离{vwap_diff:+.2f}%)")
            
            if volume_info:
                formatted += f"  {' | '.join(volume_info)}\n"
            
            volatility_info = []
            if 'ATR_percent' in latest:
                volatility_info.append(f"ATR: {latest.get('ATR_percent', 0):.2f}%")
            
            if 'HV' in latest:
                volatility_info.append(f"历史波动率: {latest.get('HV', 0):.1f}%")
            
            if volatility_info:
                formatted += f"  波动率: {' | '.join(volatility_info)}\n"
        
        formatted += f"""
=== 账户信息 ===
总资金: ${account_info.get('total_balance', 0):.2f}
可用资金: ${account_info.get('available', 0):.2f}
已用保证金: ${account_info.get('margin_used', 0):.2f}
未实现盈亏: ${account_info.get('unrealized_pnl', 0):.2f}
账户权益: ${account_info.get('equity', 0):.2f}

"""
        
        if positions:
            formatted += "=== 当前持仓 ===\n"
            for pos in positions:
                formatted += f"[{pos['position_id']}] {pos['direction'].upper()} "
                formatted += f"${pos['amount']:.2f} @ {pos['leverage']}x\n"
                formatted += f"  入场: ${pos['entry_price']:.2f} | 当前: ${pos['current_price']:.2f}\n"
                formatted += f"  盈亏: ${pos['unrealized_pnl']:.2f} ({pos['pnl_percent']:.2f}%)\n"
                formatted += f"  止损: ${pos['stop_loss']:.2f} | 止盈: ${pos['take_profit']:.2f}\n"
                formatted += f"  持仓时长: {int(pos['hold_time_seconds']//60)}分钟\n\n"
        else:
            formatted += "=== 当前持仓 ===\n无持仓\n\n"
        
        if plans:
            formatted += "=== 待触发计划 ===\n"
            for plan in plans:
                formatted += f"[{plan['plan_id']}] 触发价${plan['trigger_price']:.2f} "
                formatted += f"{plan['direction'].upper()} ${plan['amount']:.2f} @ {plan['leverage']}x\n"
                formatted += f"  止损: ${plan['stop_loss']:.2f} | 止盈: ${plan['take_profit']:.2f}\n\n"
        else:
            formatted += "=== 待触发计划 ===\n无计划\n\n"
        
        if alerts:
            formatted += "=== 价格预警 ===\n"
            for alert in alerts:
                formatted += f"[{alert['alert_id']}] {alert['condition'].upper()} ${alert['price']:.2f}\n"
                formatted += f"  说明: {alert.get('description', '无')}\n"
                formatted += f"  创建时间: {alert['create_time']}\n\n"
        else:
            formatted += "=== 价格预警 ===\n无预警\n\n"
        
        return formatted