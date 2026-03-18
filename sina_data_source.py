"""
新浪财经数据源 - 获取 A 股/港股/美股指数估值数据

无需 Token，免费使用
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SinaIndexData:
    """新浪财经指数数据获取器"""
    
    # A 股指数代码映射
    A_SHARE_INDICES = {
        "000001": "上证指数",
        "000016": "上证 50",
        "000300": "沪深 300",
        "000905": "中证 500",
        "000852": "中证 1000",
        "000688": "科创 50",
        "000922": "中证红利",
        "000925": "基本面 50",
        "000926": "基本面 60",
        "000927": "基本面 120",
        "000096": "50AH 优选",
        "399001": "深证成指",
        "399005": "中小 100",
        "399006": "创业板指",
        "399300": "沪深 300",
        "399905": "中证 500",
    }
    
    # 港股指数代码映射
    HK_INDICES = {
        "HSI": "恒生指数",
        "HSCEI": "恒生国企",
        "HSTECH": "恒生科技",
    }
    
    # 美股指数代码映射
    US_INDICES = {
        ".DJI": "道琼斯",
        ".INX": "标普 500",
        ".IXIC": "纳斯达克",
        ".NDX": "纳斯达克 100",
    }
    
    def get_index_current(self, symbol_code: str, market: str = "A") -> dict:
        """
        获取指数当前行情
        
        Args:
            symbol_code: 指数代码
            market: 市场类型 (A/HK/US)
            
        Returns:
            dict with pe, pb, dividend_yield, etc.
        """
        if market == "A":
            url = f"http://hq.sinajs.cn/list={symbol_code}"
        elif market == "HK":
            url = f"http://hq.sinajs.cn/list=rt_hk{symbol_code}"
        elif market == "US":
            url = f"http://hq.sinajs.cn/list={symbol_code}"
        else:
            return None
        
        try:
            response = requests.get(url, timeout=5)
            response.encoding = 'gbk'
            data = response.text
            
            if not data or '=' not in data:
                return None
            
            # 解析数据
            parts = data.split('=')
            if len(parts) < 2:
                return None
            
            values = parts[1].strip('"').split(',')
            
            result = {
                'code': symbol_code,
                'name': self.A_SHARE_INDICES.get(symbol_code, symbol_code),
                'price': float(values[2]) if len(values) > 2 and values[2] else None,
                'open': float(values[1]) if len(values) > 1 and values[1] else None,
                'high': float(values[3]) if len(values) > 3 and values[3] else None,
                'low': float(values[4]) if len(values) > 4 and values[4] else None,
                'pre_close': float(values[0]) if len(values) > 0 and values[0] else None,
            }
            
            # 计算涨跌幅
            if result['price'] and result['pre_close']:
                result['change_pct'] = (result['price'] - result['pre_close']) / result['pre_close'] * 100
            else:
                result['change_pct'] = None
            
            return result
            
        except Exception as e:
            logger.error(f"获取 {symbol_code} 失败：{e}")
            return None
    
    def get_index_valuation(self, symbol_code: str) -> dict:
        """
        获取指数估值数据（PE/PB/股息率）
        
        从东方财富网获取
        """
        try:
            # 东方财富指数估值接口
            url = f"https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": f"1.{symbol_code}",
                "fields": "f9,f10,f11,f12,f13,f14,f20,f23,f37,f38,f39,f40",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b"
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('data'):
                d = data['data']
                return {
                    'code': symbol_code,
                    'name': d.get('name', ''),
                    'pe': d.get('f9'),  # 市盈率
                    'pb': d.get('f10'),  # 市净率
                    'ps': d.get('f11'),  # 市销率
                    'dividend_yield': d.get('f23'),  # 股息率
                    'total_mv': d.get('f20'),  # 总市值
                    'float_mv': d.get('f37'),  # 流通市值
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取估值失败：{e}")
            return None
    
    def get_history_data(self, symbol_code: str, days: int = 250) -> pd.DataFrame:
        """
        获取历史行情数据（用于计算百分位）
        
        Args:
            symbol_code: 指数代码
            days: 历史天数（默认 250 天≈1 年）
        """
        try:
            # 东方财富历史行情接口
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
            
            url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                "secid": f"1.{symbol_code}",
                "klt": 101,  # 日 K
                "fqt": 1,  # 前复权
                "beg": start_date,
                "end": end_date,
                "fields": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                records = []
                for line in klines:
                    parts = line.split(',')
                    if len(parts) >= 11:
                        records.append({
                            'date': parts[0],
                            'open': float(parts[1]) if parts[1] else None,
                            'close': float(parts[2]) if parts[2] else None,
                            'high': float(parts[3]) if parts[3] else None,
                            'low': float(parts[4]) if parts[4] else None,
                            'volume': float(parts[5]) if parts[5] else None,
                            'amount': float(parts[6]) if parts[6] else None,
                            'amplitude': float(parts[7]) if parts[7] else None,
                            'change_pct': float(parts[8]) if parts[8] else None,
                            'change_amount': float(parts[9]) if parts[9] else None,
                            'turnover': float(parts[10]) if parts[10] else None,
                        })
                
                df = pd.DataFrame(records)
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取历史数据失败：{e}")
            return pd.DataFrame()
    
    def calculate_percentile(self, current_value: float, history: pd.Series) -> float:
        """计算百分位"""
        if history.empty or current_value is None:
            return 50.0
        
        # 计算当前值在历史数据中的百分位
        percentile = (history < current_value).sum() / len(history) * 100
        return round(percentile, 2)


def main():
    """测试函数"""
    sina = SinaIndexData()
    
    # 测试几个指数
    test_indices = [
        ("000300", "沪深 300"),
        ("000922", "中证红利"),
        ("000688", "科创 50"),
    ]
    
    for code, name in test_indices:
        print(f"\n{'='*50}")
        print(f"测试：{name} ({code})")
        print('='*50)
        
        # 获取当前行情
        current = sina.get_index_current(code)
        if current:
            print(f"当前价格：{current['price']}")
            print(f"涨跌幅：{current['change_pct']:.2f}%" if current['change_pct'] else "涨跌幅：N/A")
        
        # 获取估值数据
        valuation = sina.get_index_valuation(code)
        if valuation:
            print(f"\n估值数据:")
            print(f"  PE: {valuation['pe']}")
            print(f"  PB: {valuation['pb']}")
            print(f"  股息率：{valuation['dividend_yield']}")
        
        # 获取历史数据并计算百分位
        history = sina.get_history_data(code, days=250)
        if not history.empty and valuation and valuation.get('pe'):
            pe_percentile = sina.calculate_percentile(valuation['pe'], history['close'])
            print(f"\nPE 百分位（近 1 年）: {pe_percentile:.2f}%")


if __name__ == "__main__":
    main()
