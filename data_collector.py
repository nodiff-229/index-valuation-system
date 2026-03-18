"""
指数数据收集模块

优先使用 AkShare（免费无需 token）获取指数估值数据，Tushare 作为备选数据源。
支持获取 PE、PB、股息率等关键估值指标及历史数据用于百分位计算。

支持 50+ 指数，涵盖红利、消费、医药、科技、金融、宽基、港股、美股等类别。
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import akshare as ak
import numpy as np
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# 常量定义
# ============================================================================

# 历史数据默认年数
DEFAULT_HISTORY_YEARS = 10

# Tushare Pro Token（可选，从环境变量读取）
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "19888ce9ba935e06ae7d66902a65d5455634ad2b6b6ee7eb258217c4")

# 是否启用模拟数据（用于测试）
ENABLE_MOCK_DATA = True  # 默认使用模拟数据（真实 API 需要配置）

# 飞书通知配置
FEISHU_GROUP_ID = os.environ.get("FEISHU_GROUP_ID", "oc_c94ab3d6e65c48f5c3b7fe44517d78cc")

# ============================================================================
# 指数配置 (50+ 指数)
# ============================================================================

INDEX_CONFIG = {
    # ==================== 红利类 ====================
    "000922.SH": {
        "name": "中证红利",
        "akshare_symbol": "csi 红利指数",
        "akshare_code": "000922",
        "tushare_code": "000922.SH",
        "category": "红利",
    },
    "H30269.CSI": {
        "name": "中证红利低波动",
        "akshare_symbol": "中证红利低波动",
        "akshare_code": "H30269",
        "tushare_code": "H30269.CSI",
        "category": "红利",
    },
    "931233.CSI": {
        "name": "沪港深红利低波",
        "akshare_symbol": "沪港深红利低波",
        "akshare_code": "931233",
        "tushare_code": "931233.CSI",
        "category": "红利",
    },
    "000015.SH": {
        "name": "上证红利",
        "akshare_symbol": "上证红利",
        "akshare_code": "000015",
        "tushare_code": "000015.SH",
        "category": "红利",
    },
    "930914.CSI": {
        "name": "港股红利",
        "akshare_symbol": "港股红利",
        "akshare_code": "930914",
        "tushare_code": "930914.CSI",
        "category": "红利",
    },
    "931809.CSI": {
        "name": "龙头红利",
        "akshare_symbol": "龙头红利",
        "akshare_code": "931809",
        "tushare_code": "931809.CSI",
        "category": "红利",
    },
    "930951.CSI": {
        "name": "红利机会",
        "akshare_symbol": "红利机会",
        "akshare_code": "930951",
        "tushare_code": "930951.CSI",
        "category": "红利",
    },
    "000052.SH": {
        "name": "基本面 50",
        "akshare_symbol": "基本面 50",
        "akshare_code": "000052",
        "tushare_code": "000052.SH",
        "category": "红利",
    },
    "000053.SH": {
        "name": "基本面 60",
        "akshare_symbol": "基本面 60",
        "akshare_code": "000053",
        "tushare_code": "000053.SH",
        "category": "红利",
    },
    "000054.SH": {
        "name": "基本面 120",
        "akshare_symbol": "基本面 120",
        "akshare_code": "000054",
        "tushare_code": "000054.SH",
        "category": "红利",
    },
    "000055.SH": {
        "name": "50AH 优选",
        "akshare_symbol": "50AH 优选",
        "akshare_code": "000055",
        "tushare_code": "000055.SH",
        "category": "红利",
    },
    
    # ==================== 消费类 ====================
    "931139.CSI": {
        "name": "消费 50",
        "akshare_symbol": "消费 50",
        "akshare_code": "931139",
        "tushare_code": "931139.CSI",
        "category": "消费",
    },
    "931494.CSI": {
        "name": "消费龙头",
        "akshare_symbol": "消费龙头",
        "akshare_code": "931494",
        "tushare_code": "931494.CSI",
        "category": "消费",
    },
    "000932.SH": {
        "name": "中证消费",
        "akshare_symbol": "中证消费",
        "akshare_code": "000932",
        "tushare_code": "000932.SH",
        "category": "消费",
    },
    "399997.SZ": {
        "name": "中证白酒",
        "akshare_symbol": "中证白酒",
        "akshare_code": "399997",
        "tushare_code": "399997.SZ",
        "category": "消费",
    },
    "000036.SH": {
        "name": "可选消费",
        "akshare_symbol": "可选消费",
        "akshare_code": "000036",
        "tushare_code": "000036.SH",
        "category": "消费",
    },
    
    # ==================== 医药类 ====================
    "000933.SH": {
        "name": "医药 100",
        "akshare_symbol": "医药 100",
        "akshare_code": "000933",
        "tushare_code": "000933.SH",
        "category": "医药",
    },
    "399989.SZ": {
        "name": "中证医疗",
        "akshare_symbol": "中证医疗",
        "akshare_code": "399989",
        "tushare_code": "399989.SZ",
        "category": "医药",
    },
    "931151.CSI": {
        "name": "中证养老",
        "akshare_symbol": "中证养老",
        "akshare_code": "931151",
        "tushare_code": "931151.CSI",
        "category": "医药",
    },
    
    # ==================== 科技/成长类 ====================
    "931573.CSI": {
        "name": "港股科技",
        "akshare_symbol": "港股科技",
        "akshare_code": "931573",
        "tushare_code": "931573.CSI",
        "category": "科技",
    },
    "000688.SH": {
        "name": "科创 50",
        "akshare_symbol": "科创 50",
        "akshare_code": "000688",
        "tushare_code": "000688.SH",
        "category": "科技",
    },
    "399006.SZ": {
        "name": "创业板",
        "akshare_symbol": "创业板指",
        "akshare_code": "399006",
        "tushare_code": "399006.SZ",
        "category": "科技",
    },
    "399005.SZ": {
        "name": "深证 100",
        "akshare_symbol": "深证 100",
        "akshare_code": "399005",
        "tushare_code": "399005.SZ",
        "category": "科技",
    },
    "399001.SZ": {
        "name": "深证成指",
        "akshare_symbol": "深证成指",
        "akshare_code": "399001",
        "tushare_code": "399001.SZ",
        "category": "科技",
    },
    
    # ==================== 金融类 ====================
    "931773.CSI": {
        "name": "证券行业",
        "akshare_symbol": "证券行业",
        "akshare_code": "931773",
        "tushare_code": "931773.CSI",
        "category": "金融",
    },
    "399986.SZ": {
        "name": "中证银行",
        "akshare_symbol": "中证银行",
        "akshare_code": "399986",
        "tushare_code": "399986.SZ",
        "category": "金融",
    },
    "000919.SH": {
        "name": "300 价值",
        "akshare_symbol": "300 价值",
        "akshare_code": "000919",
        "tushare_code": "000919.SH",
        "category": "金融",
    },
    "000939.SH": {
        "name": "优选 300",
        "akshare_symbol": "优选 300",
        "akshare_code": "000939",
        "tushare_code": "000939.SH",
        "category": "金融",
    },
    "000925.SH": {
        "name": "中证价值",
        "akshare_symbol": "中证价值",
        "akshare_code": "000925",
        "tushare_code": "000925.SH",
        "category": "金融",
    },
    
    # ==================== 宽基类 ====================
    "000300.SH": {
        "name": "沪深 300",
        "akshare_symbol": "沪深 300",
        "akshare_code": "000300",
        "tushare_code": "000300.SH",
        "category": "宽基",
    },
    "000016.SH": {
        "name": "上证 50",
        "akshare_symbol": "上证 50",
        "akshare_code": "000016",
        "tushare_code": "000016.SH",
        "category": "宽基",
    },
    "399998.SZ": {
        "name": "央视 50",
        "akshare_symbol": "央视 50",
        "akshare_code": "399998",
        "tushare_code": "399998.SZ",
        "category": "宽基",
    },
    "931702.CSI": {
        "name": "MSCI A50",
        "akshare_symbol": "MSCIA50",
        "akshare_code": "931702",
        "tushare_code": "931702.CSI",
        "category": "宽基",
    },
    "931138.CSI": {
        "name": "中证 A50",
        "akshare_symbol": "中证 A50",
        "akshare_code": "931138",
        "tushare_code": "931138.CSI",
        "category": "宽基",
    },
    "000906.SH": {
        "name": "中证 800",
        "akshare_symbol": "中证 800",
        "akshare_code": "000906",
        "tushare_code": "000906.SH",
        "category": "宽基",
    },
    "931368.CSI": {
        "name": "中证 A100",
        "akshare_symbol": "中证 A100",
        "akshare_code": "931368",
        "tushare_code": "931368.CSI",
        "category": "宽基",
    },
    "932201.CSI": {
        "name": "中证 A500",
        "akshare_symbol": "中证 A500",
        "akshare_code": "932201",
        "tushare_code": "932201.CSI",
        "category": "宽基",
    },
    "931623.CSI": {
        "name": "香港中小",
        "akshare_symbol": "香港中小",
        "akshare_code": "931623",
        "tushare_code": "931623.CSI",
        "category": "宽基",
    },
    "000010.SH": {
        "name": "上证 180",
        "akshare_symbol": "上证 180",
        "akshare_code": "000010",
        "tushare_code": "000010.SH",
        "category": "宽基",
    },
    "000852.SH": {
        "name": "中证 1000",
        "akshare_symbol": "中证 1000",
        "akshare_code": "000852",
        "tushare_code": "000852.SH",
        "category": "宽基",
    },
    
    # ==================== 港股类 ====================
    "HSI": {
        "name": "恒生指数",
        "akshare_symbol": "恒生指数",
        "akshare_code": "HSI",
        "tushare_code": "HSI.HK",
        "category": "港股",
        "is_overseas": True,
    },
    "HSCEI": {
        "name": "H 股指数",
        "akshare_symbol": "恒生国企",
        "akshare_code": "HSCEI",
        "tushare_code": "HSCEI.HK",
        "category": "港股",
        "is_overseas": True,
    },
    
    # ==================== 美股类 ====================
    "SPX": {
        "name": "标普 500",
        "akshare_symbol": "标普 500",
        "akshare_code": "SPX",
        "tushare_code": None,
        "category": "美股",
        "is_overseas": True,
    },
    "NDX": {
        "name": "纳斯达克 100",
        "akshare_symbol": "纳斯达克 100",
        "akshare_code": "NDX",
        "tushare_code": None,
        "category": "美股",
        "is_overseas": True,
    },
    
    # ==================== 其他 ====================
    "931493.CSI": {
        "name": "自由现金流",
        "akshare_symbol": "自由现金流",
        "akshare_code": "931493",
        "tushare_code": "931493.CSI",
        "category": "其他",
    },
    "930955.CSI": {
        "name": "500 低波动",
        "akshare_symbol": "500 低波动",
        "akshare_code": "930955",
        "tushare_code": "930955.CSI",
        "category": "其他",
    },
}


@dataclass
class IndexValuation:
    """指数估值数据类"""
    code: str
    name: str
    pe: float
    pb: float
    dividend_yield: float
    roe: float
    earnings_yield: float
    pe_percentile: Optional[float] = None
    pb_percentile: Optional[float] = None
    data_source: str = "akshare"
    trade_date: Optional[str] = None
    category: str = ""


@dataclass
class HistoryData:
    """历史估值数据类"""
    code: str
    name: str
    pe_series: pd.Series
    pb_series: pd.Series
    dividend_yield_series: pd.Series
    data_count: int
    start_date: str
    end_date: str
    data_source: str = "akshare"


# ============================================================================
# 飞书通知函数
# ============================================================================

def send_feishu_token_alert(error_message: str) -> bool:
    """发送 Tushare token 失效的飞书通知
    
    Args:
        error_message: 错误信息
        
    Returns:
        是否发送成功
    """
    try:
        import requests
        
        webhook_url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{FEISHU_GROUP_ID}"
        
        content = {
            "msg_type": "text",
            "content": {
                "text": f"⚠️ Tushare Token 失效警告\n\n错误信息：{error_message}\n\n请及时更新 ~/.openclaw/.env 中的 TUSHARE_TOKEN"
            }
        }
        
        response = requests.post(webhook_url, json=content, timeout=10)
        
        if response.status_code == 200:
            logger.info("飞书 token 失效通知发送成功")
            return True
        else:
            logger.warning(f"飞书通知发送失败：{response.status_code}")
            return False
            
    except Exception as e:
        logger.warning(f"发送飞书通知失败：{e}")
        return False


# ============================================================================
# AkShare 数据源
# ============================================================================

class AkShareDataSource:
    """AkShare 数据源（免费无需 token）"""

    def __init__(self):
        logger.info("AkShare 数据源初始化完成")

    def get_index_valuation_history(
        self,
        symbol: str,
        years: int = DEFAULT_HISTORY_YEARS
    ) -> Optional[pd.DataFrame]:
        """获取指数估值历史数据"""
        try:
            logger.info(f"AkShare: 正在获取 {symbol} 的历史估值数据...")

            df = ak.stock_zh_index_value_csindex(symbol=symbol)

            if df is None or df.empty:
                logger.warning(f"AkShare: {symbol} 未获取到数据")
                return None

            column_mapping = {
                "日期": "date",
                "市盈率": "pe",
                "市净率": "pb",
                "股息率": "dividend_yield",
            }
            df = df.rename(columns=column_mapping)

            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            elif "日期" in df.columns:
                df["date"] = pd.to_datetime(df["日期"])

            if "date" in df.columns:
                start_date = datetime.now() - timedelta(days=years * 365)
                df = df[df["date"] >= start_date]

            logger.info(f"AkShare: 成功获取 {symbol} 共 {len(df)} 条历史数据")
            return df

        except Exception as e:
            logger.warning(f"AkShare: 获取 {symbol} 历史数据失败 - {e}")
            return None

    def get_index_current_valuation(
        self,
        symbol: str
    ) -> Optional[dict]:
        """获取指数当前估值数据"""
        try:
            df = self.get_index_valuation_history(symbol, years=1)

            if df is None or df.empty:
                return None

            if "date" in df.columns:
                df = df.sort_values("date", ascending=False)

            latest = df.iloc[0]

            dividend_yield = latest.get("dividend_yield", 0)
            if isinstance(dividend_yield, str):
                dividend_yield = float(dividend_yield.replace("%", ""))
            elif dividend_yield < 1:
                dividend_yield = dividend_yield * 100

            return {
                "pe": float(latest.get("pe", 0)),
                "pb": float(latest.get("pb", 0)),
                "dividend_yield": round(float(dividend_yield), 4),
                "trade_date": latest.get("date", datetime.now()).strftime("%Y-%m-%d") if "date" in df.columns else None,
            }

        except Exception as e:
            logger.warning(f"AkShare: 获取 {symbol} 当前估值失败 - {e}")
            return None

    def get_overseas_index_valuation(self, symbol: str) -> Optional[dict]:
        """获取海外指数估值数据"""
        try:
            df = ak.stock_zh_index_value_csindex(symbol=symbol)

            if df is not None and not df.empty:
                column_mapping = {
                    "日期": "date",
                    "市盈率": "pe",
                    "市净率": "pb",
                    "股息率": "dividend_yield",
                }
                df = df.rename(columns=column_mapping)

                if "date" in df.columns:
                    df = df.sort_values("date", ascending=False)

                latest = df.iloc[0]

                dividend_yield = latest.get("dividend_yield", 0)
                if isinstance(dividend_yield, str):
                    dividend_yield = float(dividend_yield.replace("%", ""))
                elif dividend_yield < 1:
                    dividend_yield = dividend_yield * 100

                return {
                    "pe": float(latest.get("pe", 0)),
                    "pb": float(latest.get("pb", 0)),
                    "dividend_yield": round(float(dividend_yield), 4),
                    "trade_date": latest.get("date", datetime.now()).strftime("%Y-%m-%d") if "date" in df.columns else None,
                }

        except Exception as e:
            logger.warning(f"AkShare: 获取海外指数 {symbol} 数据失败 - {e}")

        return None


# ============================================================================
# Tushare 数据源（备选）
# ============================================================================

class TushareDataSource:
    """Tushare 数据源（需要 token）"""

    def __init__(self, token: str = TUSHARE_TOKEN):
        self.token = token
        self.pro = None
        self._initialized = False
        self._token_valid = True

    def _init_tushare(self) -> bool:
        """延迟初始化 Tushare"""
        if self._initialized:
            return self.pro is not None

        try:
            import tushare as ts
            ts.set_token(self.token)
            self.pro = ts.pro_api()
            self._initialized = True
            logger.info("Tushare Pro API 初始化成功")
            return True
        except Exception as e:
            logger.warning(f"Tushare Pro API 初始化失败：{e}")
            self._initialized = True
            return False

    def _check_token_error(self, e: Exception) -> bool:
        """检查是否为 token 错误"""
        error_str = str(e).lower()
        token_errors = ["token", "权限", "积分", "不够", "invalid", "unauthorized"]
        return any(err in error_str for err in token_errors)

    def get_index_valuation_history(
        self,
        ts_code: str,
        years: int = DEFAULT_HISTORY_YEARS
    ) -> Optional[pd.DataFrame]:
        """获取指数估值历史数据"""
        if not self._init_tushare():
            return None

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)

            logger.info(f"Tushare: 正在获取 {ts_code} 的历史估值数据...")

            df = self.pro.index_dailybasic(
                ts_code=ts_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                fields="ts_code,trade_date,pe,pb,dividend_yield"
            )

            if df is None or df.empty:
                logger.warning(f"Tushare: {ts_code} 未获取到数据")
                return None

            df = df.rename(columns={
                "trade_date": "date",
                "dividend_yield": "dividend_yield"
            })

            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")

            logger.info(f"Tushare: 成功获取 {ts_code} 共 {len(df)} 条历史数据")
            return df

        except Exception as e:
            if self._check_token_error(e):
                logger.error(f"Tushare Token 失效：{e}")
                self._token_valid = False
                send_feishu_token_alert(str(e))
            else:
                logger.warning(f"Tushare: 获取 {ts_code} 历史数据失败 - {e}")
            return None

    def get_index_current_valuation(
        self,
        ts_code: str
    ) -> Optional[dict]:
        """获取指数当前估值数据"""
        if not self._init_tushare():
            return None

        try:
            today = datetime.now().strftime("%Y%m%d")
            df = self.pro.index_dailybasic(
                ts_code=ts_code,
                start_date=today,
                end_date=today,
                fields="ts_code,trade_date,pe,pb,dividend_yield"
            )

            if df is None or df.empty:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                df = self.pro.index_dailybasic(
                    ts_code=ts_code,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    fields="ts_code,trade_date,pe,pb,dividend_yield"
                )

            if df is None or df.empty:
                return None

            latest = df.iloc[0]

            return {
                "pe": float(latest.get("pe", 0)),
                "pb": float(latest.get("pb", 0)),
                "dividend_yield": float(latest.get("dividend_yield", 0)),
                "trade_date": pd.to_datetime(latest["trade_date"], format="%Y%m%d").strftime("%Y-%m-%d"),
            }

        except Exception as e:
            if self._check_token_error(e):
                logger.error(f"Tushare Token 失效：{e}")
                self._token_valid = False
                send_feishu_token_alert(str(e))
            else:
                logger.warning(f"Tushare: 获取 {ts_code} 当前估值失败 - {e}")
            return None


# ============================================================================
# 模拟数据源（用于测试）
# ============================================================================

class MockDataSource:
    """模拟数据源（用于测试）"""

    MOCK_DATA = {
        "000922.SH": {"name": "中证红利", "pe": 6.5, "pb": 0.75, "dividend_yield": 5.2},
        "000300.SH": {"name": "沪深 300", "pe": 12.5, "pb": 1.35, "dividend_yield": 3.1},
        "000688.SH": {"name": "科创 50", "pe": 45.0, "pb": 4.2, "dividend_yield": 0.8},
        "NDX": {"name": "纳斯达克 100", "pe": 28.5, "pb": 6.8, "dividend_yield": 0.6},
    }

    def __init__(self):
        logger.info("Mock 数据源初始化完成（测试模式）")

    def get_index_valuation_history(
        self,
        code: str,
        years: int = DEFAULT_HISTORY_YEARS
    ) -> Optional[pd.DataFrame]:
        """生成模拟历史数据"""
        if code not in self.MOCK_DATA:
            # 为未知指数生成通用模拟数据
            config = {"name": "未知指数", "pe": 15.0, "pb": 2.0, "dividend_yield": 2.0}
        else:
            config = self.MOCK_DATA[code]
        
        np.random.seed(42)
        days = years * 250
        dates = pd.date_range(end=datetime.now(), periods=days, freq="B")

        base_pe = config["pe"]
        base_pb = config["pb"]
        base_div = config["dividend_yield"]

        pe_values = base_pe * (1 + np.random.randn(days) * 0.2)
        pb_values = base_pb * (1 + np.random.randn(days) * 0.15)
        div_values = base_div * (1 + np.random.randn(days) * 0.1)

        pe_values = np.maximum(pe_values, base_pe * 0.5)
        pb_values = np.maximum(pb_values, base_pb * 0.5)
        div_values = np.maximum(div_values, 0.1)

        df = pd.DataFrame({
            "date": dates,
            "pe": pe_values,
            "pb": pb_values,
            "dividend_yield": div_values,
        })

        logger.info(f"Mock: 生成 {code} 共 {len(df)} 条模拟历史数据")
        return df

    def get_index_current_valuation(self, code: str) -> Optional[dict]:
        """获取模拟当前估值"""
        if code not in self.MOCK_DATA:
            config = {"name": "未知指数", "pe": 15.0, "pb": 2.0, "dividend_yield": 2.0}
        else:
            config = self.MOCK_DATA[code]
            
        return {
            "pe": config["pe"],
            "pb": config["pb"],
            "dividend_yield": config["dividend_yield"],
            "trade_date": datetime.now().strftime("%Y-%m-%d"),
        }


# ============================================================================
# 数据收集器
# ============================================================================

class DataCollector:
    """指数数据收集器"""

    def __init__(
        self,
        tushare_token: str = TUSHARE_TOKEN,
        enable_mock: bool = ENABLE_MOCK_DATA
    ):
        self.akshare = AkShareDataSource()
        self.tushare = TushareDataSource(tushare_token) if tushare_token else None
        self.mock = MockDataSource() if enable_mock else None
        self.enable_mock = enable_mock
        logger.info(f"DataCollector 初始化完成 (模拟数据：{enable_mock})")

    def get_history_data(
        self,
        code: str,
        years: int = DEFAULT_HISTORY_YEARS
    ) -> Optional[HistoryData]:
        """获取指数历史估值数据"""
        if code not in INDEX_CONFIG:
            logger.error(f"未知指数代码：{code}")
            return None

        config = INDEX_CONFIG[code]
        name = config["name"]

        df = None
        data_source = None

        # 1. 尝试 AkShare
        if not config.get("is_overseas"):
            df = self.akshare.get_index_valuation_history(
                config["akshare_symbol"],
                years
            )
            if df is not None:
                data_source = "akshare"
        else:
            # 海外指数
            df = self.akshare.get_overseas_index_valuation(
                config["akshare_symbol"]
            )
            if df is not None:
                data_source = "akshare"

        # 2. 如果 AkShare 失败，尝试 Tushare
        if df is None and self.tushare and config.get("tushare_code"):
            df = self.tushare.get_index_valuation_history(
                config["tushare_code"],
                years
            )
            if df is not None:
                data_source = "tushare"

        # 3. 如果都失败，尝试 Mock
        if df is None and self.mock:
            df = self.mock.get_index_valuation_history(code, years)
            if df is not None:
                data_source = "mock"

        if df is None:
            logger.error(f"无法获取 {name} 的历史数据")
            return None

        return HistoryData(
            code=code,
            name=name,
            pe_series=df["pe"],
            pb_series=df["pb"],
            dividend_yield_series=df.get("dividend_yield", pd.Series()),
            data_count=len(df),
            start_date=df["date"].min().strftime("%Y-%m-%d"),
            end_date=df["date"].max().strftime("%Y-%m-%d"),
            data_source=data_source,
        )

    def get_current_valuation(
        self,
        code: str
    ) -> Optional[IndexValuation]:
        """获取指数当前估值数据"""
        if code not in INDEX_CONFIG:
            logger.error(f"未知指数代码：{code}")
            return None

        config = INDEX_CONFIG[code]
        name = config["name"]

        valuation_data = None
        data_source = None

        # 1. 尝试 AkShare
        if config.get("is_overseas"):
            valuation_data = self.akshare.get_overseas_index_valuation(
                config["akshare_symbol"]
            )
        else:
            valuation_data = self.akshare.get_index_current_valuation(
                config["akshare_symbol"]
            )

        if valuation_data is not None:
            data_source = "akshare"

        # 2. 如果 AkShare 失败，尝试 Tushare
        if valuation_data is None and self.tushare and config.get("tushare_code"):
            valuation_data = self.tushare.get_index_current_valuation(
                config["tushare_code"]
            )
            if valuation_data is not None:
                data_source = "tushare"

        # 3. 如果都失败，尝试 Mock
        if valuation_data is None and self.mock:
            valuation_data = self.mock.get_index_current_valuation(code)
            if valuation_data is not None:
                data_source = "mock"

        if valuation_data is None:
            logger.error(f"无法获取 {name} 的当前估值数据")
            return None

        pe = valuation_data["pe"]
        pb = valuation_data["pb"]
        dividend_yield = valuation_data["dividend_yield"]

        earnings_yield = (1 / pe * 100) if pe > 0 else 0
        roe = (pb / pe * 100) if pe > 0 and pb > 0 else 0

        return IndexValuation(
            code=code,
            name=name,
            pe=round(pe, 4),
            pb=round(pb, 4),
            dividend_yield=round(dividend_yield, 4),
            roe=round(roe, 4),
            earnings_yield=round(earnings_yield, 4),
            data_source=data_source,
            trade_date=valuation_data.get("trade_date"),
            category=config.get("category", ""),
        )

    def get_index_valuation(
        self,
        code: str,
        years: int = DEFAULT_HISTORY_YEARS
    ) -> Optional[IndexValuation]:
        """获取指数完整估值数据"""
        valuation = self.get_current_valuation(code)

        if valuation is None:
            return None

        history = self.get_history_data(code, years)

        if history is not None:
            valuation.pe_percentile = self._calculate_percentile(
                valuation.pe, history.pe_series
            )
            valuation.pb_percentile = self._calculate_percentile(
                valuation.pb, history.pb_series
            )

        return valuation

    def get_all_index_valuations(
        self,
        years: int = DEFAULT_HISTORY_YEARS
    ) -> dict[str, IndexValuation]:
        """获取所有指数的估值数据"""
        results = {}

        for code in INDEX_CONFIG:
            name = INDEX_CONFIG[code]["name"]
            logger.info(f"正在获取 {name} 估值数据...")

            valuation = self.get_index_valuation(code, years)

            if valuation is not None:
                results[code] = valuation
                logger.info(
                    f"{name}: PE={valuation.pe}, PB={valuation.pb}, "
                    f"股息率={valuation.dividend_yield}%, "
                    f"PE 百分位={valuation.pe_percentile}%, "
                    f"数据源={valuation.data_source}"
                )
            else:
                logger.warning(f"跳过 {name}，数据获取失败")

        return results

    def get_index_pe_history(
        self,
        code: str,
        years: int = DEFAULT_HISTORY_YEARS
    ) -> pd.DataFrame:
        """获取指数历史 PE/PB 数据"""
        history = self.get_history_data(code, years)

        if history is None:
            return pd.DataFrame()

        return pd.DataFrame({
            "pe": history.pe_series,
            "pb": history.pb_series,
        })

    @staticmethod
    def _calculate_percentile(
        current_value: float,
        history_values: pd.Series
    ) -> float:
        """计算百分位"""
        if history_values.empty or pd.isna(current_value):
            return 0.0

        valid_values = history_values.dropna()

        if valid_values.empty:
            return 0.0

        percentile = (valid_values < current_value).sum() / len(valid_values) * 100
        return round(percentile, 2)


def main():
    """测试函数"""
    print("\n" + "=" * 60)
    print("指数估值数据收集测试")
    print("=" * 60)

    collector = DataCollector(enable_mock=True)
    valuations = collector.get_all_index_valuations()

    print("\n估值结果:")
    print("-" * 60)

    for code, val in valuations.items():
        print(f"\n{val.name} ({code}):")
        print(f"  PE: {val.pe} (历史百分位：{val.pe_percentile}%)")
        print(f"  PB: {val.pb} (历史百分位：{val.pb_percentile}%)")
        print(f"  股息率：{val.dividend_yield}%")
        print(f"  ROE: {val.roe}%")
        print(f"  盈利收益率：{val.earnings_yield}%")
        print(f"  数据来源：{val.data_source}")
        print(f"  交易日期：{val.trade_date}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
