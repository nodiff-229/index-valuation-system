"""
Tushare Pro 数据源 - 使用 requests 直接调用 API

解决 tushare 库 token 验证问题
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TushareProAPI:
    """Tushare Pro API 客户端（使用 requests 直接调用）"""
    
    def __init__(self, token: str):
        self.token = token
        self.url = "https://api.tushare.pro"
        self.headers = {"Content-Type": "application/json"}
        self._token_valid = None
    
    def _request(self, api_name: str, params: dict = None, fields: str = "") -> dict:
        """发送 API 请求"""
        payload = {
            "token": self.token,
            "api_name": api_name,
            "params": params or {},
            "fields": fields
        }
        
        try:
            response = requests.post(self.url, json=payload, headers=self.headers, timeout=10)
            result = response.json()
            
            if result.get('code') != 0:
                msg = result.get('msg', 'Unknown error')
                logger.warning(f"Tushare API 错误 [{result.get('code')}]: {msg}")
                return None
            
            return result.get('data', {})
            
        except Exception as e:
            logger.error(f"Tushare 请求失败：{e}")
            return None
    
    def check_token(self) -> bool:
        """检查 token 是否有效"""
        if self._token_valid is not None:
            return self._token_valid
        
        result = self._request("user")
        if result:
            self._token_valid = True
            logger.info(f"✅ Tushare Token 有效！用户名：{result.get('user_name', 'N/A')}, 积分：{result.get('total_pts', 'N/A')}")
            return True
        else:
            self._token_valid = False
            logger.error("❌ Tushare Token 无效")
            return False
    
    def get_index_dailybasic(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取指数每日基本面数据
        
        Args:
            ts_code: 指数代码（如 000922.SH）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=3650)).strftime("%Y%m%d")  # 默认 10 年
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        params = {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date
        }
        
        result = self._request("index_dailybasic", params, "ts_code,trade_date,pe,pb,dividend_yield")
        if result and 'items' in result:
            df = pd.DataFrame(result['items'], columns=result['fields'])
            return df
        return pd.DataFrame()
    
    def get_index_current_valuation(self, ts_code: str) -> dict:
        """获取指数当前估值"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")
        
        df = self.get_index_dailybasic(ts_code, start_date, end_date)
        if not df.empty:
            latest = df.iloc[-1]
            return {
                'code': ts_code,
                'date': latest.get('trade_date'),
                'pe': latest.get('pe'),
                'pb': latest.get('pb'),
                'dividend_yield': latest.get('dividend_yield'),
            }
        return None
    
    def get_history_pe_pb(self, ts_code: str, years: int = 10) -> pd.DataFrame:
        """获取历史 PE/PB 数据"""
        start_date = (datetime.now() - timedelta(days=years*365)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        
        return self.get_index_dailybasic(ts_code, start_date, end_date)


# 指数代码映射
INDEX_CODES = {
    # 红利类
    "中证红利": "000922.SH",
    "中证红利低波动": "H30269.CSI",
    "上证红利": "000015.SH",
    "红利机会": "H30269.CSI",
    "基本面 50": "000925.SH",
    "基本面 60": "000926.SH",
    "基本面 120": "000927.SH",
    "50AH 优选": "000096.SH",
    
    # 宽基类
    "沪深 300": "000300.SH",
    "上证 50": "000016.SH",
    "中证 500": "000905.SH",
    "中证 1000": "000852.SH",
    "中证 800": "000906.SH",
    "创业板": "399006.SZ",
    "科创 50": "000688.SH",
}


def main():
    """测试函数"""
    token = "19888ce9ba935e06ae7d66902a65d5455634ad2b6b6ee7eb258217c4"
    api = TushareProAPI(token)
    
    # 检查 token
    print("检查 Token...")
    if not api.check_token():
        print("❌ Token 无效，退出")
        return
    
    # 测试获取数据
    print("\n测试获取中证红利数据...")
    df = api.get_history_pe_pb("000922.SH", years=1)
    print(f"✅ 获取成功！共 {len(df)} 行")
    print("\n最新数据:")
    print(df.tail())
    
    # 获取当前估值
    print("\n获取当前估值...")
    current = api.get_index_current_valuation("000922.SH")
    if current:
        print(f"  PE: {current['pe']}")
        print(f"  PB: {current['pb']}")
        print(f"  股息率：{current['dividend_yield']}")


if __name__ == "__main__":
    main()
