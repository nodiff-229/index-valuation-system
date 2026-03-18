"""
指数估值数据收集器 - 修复版

使用中证指数官网直接下载 Excel 数据，避免 Tushare token 问题
"""

import pandas as pd
import requests
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CSIndexDownloader:
    """中证指数数据下载器"""
    
    def __init__(self, cache_dir: str = "~/.openclaw/workspace/Index_Valuation/cache"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://www.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/indicator/"
    
    def download_index_data(self, symbol: str, symbol_code: str) -> pd.DataFrame:
        """
        下载指数估值数据
        
        Args:
            symbol: 指数名称（中文）
            symbol_code: 指数代码
            
        Returns:
            DataFrame with columns: date, pe, pb, ps, dividend_yield
        """
        # 检查缓存
        cache_file = self.cache_dir / f"{symbol_code}.xlsx"
        if cache_file.exists():
            logger.info(f"从缓存读取 {symbol}")
            return pd.read_excel(cache_file)
        
        # 下载数据
        encoded_symbol = urllib.parse.quote(symbol)
        url = f"{self.base_url}{encoded_symbol}indicator.xls"
        
        try:
            logger.info(f"正在下载 {symbol} 数据：{url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # 保存临时文件
            temp_file = self.cache_dir / f"{symbol_code}_temp.xls"
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            # 读取 Excel
            df = pd.read_excel(temp_file)
            
            # 保存到缓存
            df.to_excel(cache_file, index=False)
            
            # 删除临时文件
            temp_file.unlink()
            
            logger.info(f"✅ {symbol} 数据下载成功，共 {len(df)} 行")
            return df
            
        except Exception as e:
            logger.error(f"❌ {symbol} 数据下载失败：{e}")
            return None
    
    def get_current_valuation(self, symbol: str, symbol_code: str) -> dict:
        """获取当前估值数据"""
        df = self.download_index_data(symbol, symbol_code)
        if df is None or len(df) == 0:
            return None
        
        # 获取最新数据
        latest = df.iloc[-1]
        
        # 标准化列名
        result = {
            'name': symbol,
            'code': symbol_code,
            'date': latest.get('日期', latest.get('trade_date', None)),
            'pe': latest.get('市盈率', latest.get('pe', None)),
            'pb': latest.get('市净率', latest.get('pb', None)),
            'ps': latest.get('市销率', latest.get('ps', None)),
            'dividend_yield': latest.get('股息率', latest.get('dividend_yield', None)),
        }
        
        # 计算 ROE
        if result['pb'] and result['pe']:
            result['roe'] = result['pb'] / result['pe'] * 100
        else:
            result['roe'] = None
        
        return result
    
    def get_history_percentile(self, symbol: str, symbol_code: str, years: int = 10) -> dict:
        """
        计算历史百分位
        
        Args:
            symbol: 指数名称
            symbol_code: 指数代码
            years: 历史年数
            
        Returns:
            {'pe_percentile': float, 'pb_percentile': float}
        """
        df = self.download_index_data(symbol, symbol_code)
        if df is None or len(df) < 250:  # 至少 1 年数据
            return {'pe_percentile': 50.0, 'pb_percentile': 50.0}
        
        # 截取指定年数数据
        cutoff_date = datetime.now() - timedelta(days=years*365)
        df = df[df['日期'] >= cutoff_date] if '日期' in df.columns else df
        
        current = df.iloc[-1]
        history_pe = df['市盈率'].dropna() if '市盈率' in df.columns else pd.Series()
        history_pb = df['市净率'].dropna() if '市净率' in df.columns else pd.Series()
        
        # 计算百分位
        pe_percentile = (history_pe < current['市盈率']).sum() / len(history_pe) * 100 if len(history_pe) > 0 and '市盈率' in df.columns else 50.0
        pb_percentile = (history_pb < current['市净率']).sum() / len(history_pb) * 100 if len(history_pb) > 0 and '市净率' in df.columns else 50.0
        
        return {
            'pe_percentile': pe_percentile,
            'pb_percentile': pb_percentile
        }


# 指数代码映射
INDEX_CODES = {
    # 红利类
    "中证红利": "000922",
    "中证红利低波动": "H30269",
    "上证红利": "000015",
    "红利机会": "H30269",
    "基本面 50": "000925",
    "基本面 60": "000926",
    "基本面 120": "000927",
    "50AH 优选": "000096",
    
    # 宽基类
    "沪深 300": "000300",
    "上证 50": "000016",
    "中证 500": "000905",
    "中证 1000": "000852",
    "中证 800": "000906",
    "创业板": "399006",
    "科创 50": "000688",
}


def main():
    """测试函数"""
    downloader = CSIndexDownloader()
    
    # 测试几个指数
    test_indices = [
        ("中证红利", "000922"),
        ("沪深 300", "000300"),
        ("科创 50", "000688"),
    ]
    
    for symbol, code in test_indices:
        print(f"\n{'='*50}")
        print(f"测试：{symbol} ({code})")
        print('='*50)
        
        # 获取当前估值
        current = downloader.get_current_valuation(symbol, code)
        if current:
            print(f"当前估值:")
            print(f"  PE: {current['pe']}")
            print(f"  PB: {current['pb']}")
            print(f"  股息率：{current['dividend_yield']}")
            print(f"  ROE: {current['roe']:.2f}%" if current['roe'] else "  ROE: N/A")
        
        # 获取历史百分位
        percentile = downloader.get_history_percentile(symbol, code)
        print(f"历史百分位:")
        print(f"  PE 百分位：{percentile['pe_percentile']:.2f}%")
        print(f"  PB 百分位：{percentile['pb_percentile']:.2f}%")


if __name__ == "__main__":
    main()
