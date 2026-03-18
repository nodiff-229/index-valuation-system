"""
指数估值逻辑模块

实现指数估值分析的核心算法，包括：
1. 历史百分位计算：基于过去 10 年 PE/PB 数据
2. 格雷厄姆策略建议：基于盈利收益率与国债收益率的比较
3. 博格公式建议：预期收益率 = 初始股息率 + 盈利增长率 + PE 变化率
4. 估值区域划分：低估/中估/高估
5. 综合评分计算：0-100 分，分数越低越值得投资
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd


# ============================================================================
# 常量定义
# ============================================================================

DEFAULT_10Y_BOND_YIELD = 1.83
DEFAULT_HISTORY_YEARS = 10

VALUATION_THRESHOLDS = {
    "low": 30,
    "high": 70,
}

# 博格公式阈值
BURGESS_THRESHOLDS = {
    "strong_buy": 15,  # 预期收益率 > 15%
    "buy": 10,         # 预期收益率 10-15%
    "hold": 5,         # 预期收益率 5-10%
    "sell": 0,         # 预期收益率 < 5%
}


# ============================================================================
# 枚举定义
# ============================================================================

class ValuationZone(Enum):
    UNDERVALUED = "低估区"
    FAIR_VALUE = "中估区"
    OVERVALUED = "高估区"


class GrahamSignal(Enum):
    BUY = "定投信号"
    HOLD = "持有信号"
    SELL = "卖出信号"


class SignalColor(Enum):
    GREEN = "绿色"
    ORANGE = "橙色"
    RED = "红色"


class BurgessSignal(Enum):
    STRONG_BUY = "强烈推荐"
    BUY = "推荐"
    HOLD = "持有"
    SELL = "卖出"


class BurgessColor(Enum):
    DARK_GREEN = "深绿色"
    GREEN = "绿色"
    ORANGE = "橙色"
    RED = "红色"


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class PercentileResult:
    value: float
    percentile: float
    min_value: float
    max_value: float
    mean_value: float
    data_count: int


@dataclass
class ValuationAnalysis:
    pe: float
    pb: float
    earnings_yield: float
    dividend_yield: float
    pe_percentile: PercentileResult
    pb_percentile: PercentileResult
    pe_zone: ValuationZone
    pb_zone: ValuationZone
    combined_zone: ValuationZone
    graham_signal: GrahamSignal
    signal_color: SignalColor
    score: float
    bond_yield: float


@dataclass
class BurgessResult:
    """博格公式计算结果"""
    expected_return: float          # 预期收益率 (%)
    dividend_yield: float           # 初始股息率 (%)
    earnings_growth: float          # 盈利增长率 (%)
    pe_change: float               # PE 变化率 (%)
    signal: BurgessSignal          # 投资建议
    color: BurgessColor            # 颜色标识


# ============================================================================
# 核心估值逻辑类
# ============================================================================

class ValuationLogic:
    """估值逻辑计算器"""

    def __init__(
        self,
        bond_yield: float = DEFAULT_10Y_BOND_YIELD,
        history_years: int = DEFAULT_HISTORY_YEARS
    ):
        self.bond_yield = bond_yield
        self.history_years = history_years

    # ------------------------------------------------------------------------
    # 百分位计算
    # ------------------------------------------------------------------------

    def calculate_percentile(
        self,
        current_value: float,
        history_values: pd.Series
    ) -> PercentileResult:
        """计算当前值在历史数据中的百分位"""
        if pd.isna(current_value):
            raise ValueError("当前值不能为空")

        if history_values.empty:
            raise ValueError("历史数据不能为空")

        valid_values = history_values.dropna()

        if valid_values.empty:
            raise ValueError("历史数据中没有有效值")

        count_below = (valid_values < current_value).sum()
        percentile = (count_below / len(valid_values)) * 100

        return PercentileResult(
            value=round(current_value, 4),
            percentile=round(percentile, 2),
            min_value=round(float(valid_values.min()), 4),
            max_value=round(float(valid_values.max()), 4),
            mean_value=round(float(valid_values.mean()), 4),
            data_count=len(valid_values)
        )

    def calculate_percentile_simple(
        self,
        current_value: float,
        history_values: pd.Series
    ) -> float:
        """简化版百分位计算"""
        if history_values.empty or pd.isna(current_value):
            return 0.0

        valid_values = history_values.dropna()
        if valid_values.empty:
            return 0.0

        percentile = (valid_values < current_value).sum() / len(valid_values) * 100
        return round(percentile, 2)

    # ------------------------------------------------------------------------
    # 估值区域判断
    # ------------------------------------------------------------------------

    def get_valuation_zone(self, percentile: float) -> ValuationZone:
        """根据百分位判断估值区域"""
        if percentile < VALUATION_THRESHOLDS["low"]:
            return ValuationZone.UNDERVALUED
        elif percentile > VALUATION_THRESHOLDS["high"]:
            return ValuationZone.OVERVALUED
        else:
            return ValuationZone.FAIR_VALUE

    def get_combined_zone(
        self,
        pe_zone: ValuationZone,
        pb_zone: ValuationZone
    ) -> ValuationZone:
        """综合 PE 和 PB 估值区域"""
        if pe_zone == ValuationZone.UNDERVALUED and pb_zone == ValuationZone.UNDERVALUED:
            return ValuationZone.UNDERVALUED
        if pe_zone == ValuationZone.OVERVALUED and pb_zone == ValuationZone.OVERVALUED:
            return ValuationZone.OVERVALUED
        return ValuationZone.FAIR_VALUE

    # ------------------------------------------------------------------------
    # 格雷厄姆策略
    # ------------------------------------------------------------------------

    def get_graham_signal(self, earnings_yield: float) -> tuple[GrahamSignal, SignalColor]:
        """根据格雷厄姆策略给出投资建议"""
        buy_threshold = 2 * self.bond_yield
        sell_threshold = self.bond_yield

        if earnings_yield > buy_threshold:
            return GrahamSignal.BUY, SignalColor.GREEN
        elif earnings_yield <= sell_threshold:
            return GrahamSignal.SELL, SignalColor.RED
        else:
            return GrahamSignal.HOLD, SignalColor.ORANGE

    def get_graham_thresholds(self) -> dict:
        """获取格雷厄姆策略的阈值信息"""
        return {
            "buy_threshold": round(2 * self.bond_yield, 2),
            "hold_threshold": round(self.bond_yield, 2),
            "sell_threshold": round(self.bond_yield, 2),
            "bond_yield": round(self.bond_yield, 2),
        }

    # ------------------------------------------------------------------------
    # 博格公式
    # ------------------------------------------------------------------------

    def calculate_burgess_formula(
        self,
        dividend_yield: float,
        current_pe: float,
        historical_pe: float,
        earnings_growth: Optional[float] = None
    ) -> BurgessResult:
        """计算博格公式预期收益率
        
        博格公式：预期收益率 = 初始股息率 + 盈利增长率 + PE 变化率
        
        Args:
            dividend_yield: 初始股息率 (%)
            current_pe: 当前 PE
            historical_pe: 历史平均 PE（用于计算 PE 变化率）
            earnings_growth: 盈利增长率 (%)，如果为 None 则使用 ROE 估算
            
        Returns:
            BurgessResult 对象
        """
        # 1. 初始股息率（直接使用）
        init_dividend = dividend_yield
        
        # 2. 盈利增长率 - 如果没有提供，使用 ROE 估算
        # 假设留存收益率为 60%，则盈利增长率 ≈ ROE * 留存收益率
        # 简化处理：使用 ROE * 0.6 作为盈利增长率估计
        if earnings_growth is None:
            # 默认假设 ROE 为 10%，则盈利增长率约为 6%
            earnings_growth = 6.0
        
        # 3. PE 变化率 - 假设 PE 回归到历史均值
        # PE 变化率 = (历史平均 PE - 当前 PE) / 当前 PE * 100 / 年数
        # 简化：假设 10 年内 PE 回归到历史均值
        if current_pe > 0 and historical_pe > 0:
            pe_change_rate = (historical_pe - current_pe) / current_pe * 100 / self.history_years
        else:
            pe_change_rate = 0.0
        
        # 4. 计算预期收益率
        expected_return = init_dividend + earnings_growth + pe_change_rate
        
        # 5. 判断信号
        if expected_return > BURGESS_THRESHOLDS["strong_buy"]:
            signal = BurgessSignal.STRONG_BUY
            color = BurgessColor.DARK_GREEN
        elif expected_return > BURGESS_THRESHOLDS["buy"]:
            signal = BurgessSignal.BUY
            color = BurgessColor.GREEN
        elif expected_return > BURGESS_THRESHOLDS["hold"]:
            signal = BurgessSignal.HOLD
            color = BurgessColor.ORANGE
        else:
            signal = BurgessSignal.SELL
            color = BurgessColor.RED
        
        return BurgessResult(
            expected_return=round(expected_return, 2),
            dividend_yield=round(init_dividend, 2),
            earnings_growth=round(earnings_growth, 2),
            pe_change=round(pe_change_rate, 2),
            signal=signal,
            color=color,
        )

    def get_burgess_signal_for_category(
        self,
        category: str,
        dividend_yield: float,
        current_pe: float,
        historical_pe: float,
        roe: float = 10.0
    ) -> tuple[str, str]:
        """根据行业类别选择合适的估值方法
        
        Args:
            category: 行业类别（红利/消费/医药/科技/金融/宽基/港股/美股/其他）
            dividend_yield: 股息率 (%)
            current_pe: 当前 PE
            historical_pe: 历史平均 PE
            roe: ROE (%)
            
        Returns:
            (建议信号，颜色) 元组
        """
        # 稳定行业（消费/医药/红利）：使用盈利收益率法
        stable_categories = ["消费", "医药", "红利"]
        
        # 成长行业（科技）：使用博格公式法
        growth_categories = ["科技"]
        
        # 周期行业（证券/银行）：使用 PB 百分位法
        cyclical_categories = ["金融"]
        
        if category in stable_categories:
            # 盈利收益率法
            earnings_yield = (1 / current_pe * 100) if current_pe > 0 else 0
            if earnings_yield > 2 * self.bond_yield:
                return "定投买入", "绿色"
            elif earnings_yield <= self.bond_yield:
                return "分批卖出", "红色"
            else:
                return "继续持有", "橙色"
                
        elif category in growth_categories:
            # 博格公式法
            earnings_growth = roe * 0.6  # 假设留存收益率 60%
            burgess = self.calculate_burgess_formula(
                dividend_yield, current_pe, historical_pe, earnings_growth
            )
            return burgess.signal.value, burgess.color.value
            
        elif category in cyclical_categories:
            # PB 百分位法（由外部传入 PB 百分位）
            # 这里简化处理，使用 PE 百分位代替
            pe_percentile = self.calculate_percentile_simple(current_pe, pd.Series([historical_pe] * 100))
            if pe_percentile < 30:
                return "定投买入", "绿色"
            elif pe_percentile > 70:
                return "分批卖出", "红色"
            else:
                return "继续持有", "橙色"
        else:
            # 其他类别：使用综合判断
            earnings_yield = (1 / current_pe * 100) if current_pe > 0 else 0
            if earnings_yield > 2 * self.bond_yield:
                return "定投买入", "绿色"
            elif earnings_yield <= self.bond_yield:
                return "分批卖出", "红色"
            else:
                return "继续持有", "橙色"

    # ------------------------------------------------------------------------
    # 综合评分计算
    # ------------------------------------------------------------------------

    def calculate_score(
        self,
        pe_percentile: float,
        pb_percentile: float,
        earnings_yield: float,
        dividend_yield: float = 0.0
    ) -> float:
        """计算综合评分（0-100 分）"""
        WEIGHTS = {
            "pe": 0.40,
            "pb": 0.30,
            "earnings": 0.20,
            "dividend": 0.10,
        }

        pe_score = pe_percentile
        pb_score = pb_percentile

        buy_threshold = 2 * self.bond_yield
        sell_threshold = self.bond_yield

        if earnings_yield >= buy_threshold:
            earnings_score = 0
        elif earnings_yield <= sell_threshold:
            earnings_score = 100
        else:
            earnings_score = 100 - (
                (earnings_yield - sell_threshold) /
                (buy_threshold - sell_threshold) * 100
            )

        dividend_score = max(0, min(100, 100 - dividend_yield * 20))

        score = (
            pe_score * WEIGHTS["pe"] +
            pb_score * WEIGHTS["pb"] +
            earnings_score * WEIGHTS["earnings"] +
            dividend_score * WEIGHTS["dividend"]
        )

        return round(score, 2)

    # ------------------------------------------------------------------------
    # 综合分析
    # ------------------------------------------------------------------------

    def analyze(
        self,
        pe: float,
        pb: float,
        pe_history: pd.Series,
        pb_history: pd.Series,
        dividend_yield: float = 0.0
    ) -> ValuationAnalysis:
        """执行完整的估值分析"""
        if pe <= 0:
            raise ValueError("PE 必须大于 0")
        if pb <= 0:
            raise ValueError("PB 必须大于 0")

        earnings_yield = (1 / pe) * 100

        pe_percentile_result = self.calculate_percentile(pe, pe_history)
        pb_percentile_result = self.calculate_percentile(pb, pb_history)

        pe_zone = self.get_valuation_zone(pe_percentile_result.percentile)
        pb_zone = self.get_valuation_zone(pb_percentile_result.percentile)
        combined_zone = self.get_combined_zone(pe_zone, pb_zone)

        graham_signal, signal_color = self.get_graham_signal(earnings_yield)

        score = self.calculate_score(
            pe_percentile_result.percentile,
            pb_percentile_result.percentile,
            earnings_yield,
            dividend_yield
        )

        return ValuationAnalysis(
            pe=round(pe, 4),
            pb=round(pb, 4),
            earnings_yield=round(earnings_yield, 4),
            dividend_yield=round(dividend_yield, 4),
            pe_percentile=pe_percentile_result,
            pb_percentile=pb_percentile_result,
            pe_zone=pe_zone,
            pb_zone=pb_zone,
            combined_zone=combined_zone,
            graham_signal=graham_signal,
            signal_color=signal_color,
            score=score,
            bond_yield=self.bond_yield
        )


# ============================================================================
# 辅助函数
# ============================================================================

def format_valuation_report(analysis: ValuationAnalysis) -> str:
    """格式化估值分析报告为可读字符串"""
    lines = [
        "=" * 60,
        "指数估值分析报告",
        "=" * 60,
        "",
        "【基础估值指标】",
        f"  市盈率 (PE): {analysis.pe}",
        f"  市净率 (PB): {analysis.pb}",
        f"  盈利收益率：{analysis.earnings_yield}%",
        f"  股息率：{analysis.dividend_yield}%",
        "",
        "【PE 百分位分析】",
        f"  当前值：{analysis.pe_percentile.value}",
        f"  百分位：{analysis.pe_percentile.percentile}%",
        f"  历史范围：[{analysis.pe_percentile.min_value}, {analysis.pe_percentile.max_value}]",
        f"  历史均值：{analysis.pe_percentile.mean_value}",
        f"  估值区域：{analysis.pe_zone.value}",
        "",
        "【PB 百分位分析】",
        f"  当前值：{analysis.pb_percentile.value}",
        f"  百分位：{analysis.pb_percentile.percentile}%",
        f"  历史范围：[{analysis.pb_percentile.min_value}, {analysis.pb_percentile.max_value}]",
        f"  历史均值：{analysis.pb_percentile.mean_value}",
        f"  估值区域：{analysis.pb_zone.value}",
        "",
        "【综合评估】",
        f"  综合估值区域：{analysis.combined_zone.value}",
        f"  格雷厄姆信号：{analysis.graham_signal.value} ({analysis.signal_color.value})",
        f"  综合评分：{analysis.score} 分",
        "",
        "【参考信息】",
        f"  十年期国债收益率：{analysis.bond_yield}%",
        f"  格雷厄姆定投阈值：> {analysis.bond_yield * 2}%",
        f"  格雷厄姆卖出阈值：<= {analysis.bond_yield}%",
        "",
        "=" * 60,
    ]

    return "\n".join(lines)


def main():
    """示例：展示估值逻辑的使用方法"""
    import numpy as np

    print("\n" + "=" * 60)
    print("估值逻辑模块测试")
    print("=" * 60)

    logic = ValuationLogic(bond_yield=1.83)

    np.random.seed(42)
    pe_history = pd.Series(np.random.uniform(8, 25, 2500))
    pb_history = pd.Series(np.random.uniform(1.0, 3.5, 2500))

    current_pe = 12.5
    current_pb = 1.8
    dividend_yield = 3.5

    print(f"\n当前参数:")
    print(f"  PE: {current_pe}")
    print(f"  PB: {current_pb}")
    print(f"  股息率：{dividend_yield}%")
    print(f"  国债收益率：{logic.bond_yield}%")

    try:
        analysis = logic.analyze(
            pe=current_pe,
            pb=current_pb,
            pe_history=pe_history,
            pb_history=pb_history,
            dividend_yield=dividend_yield
        )
        print(format_valuation_report(analysis))
    except ValueError as e:
        print(f"\n错误：{e}")

    # 测试博格公式
    print("\n【博格公式测试】")
    burgess = logic.calculate_burgess_formula(
        dividend_yield=3.5,
        current_pe=12.5,
        historical_pe=15.0,
        earnings_growth=6.0
    )
    print(f"  预期收益率：{burgess.expected_return}%")
    print(f"  初始股息率：{burgess.dividend_yield}%")
    print(f"  盈利增长率：{burgess.earnings_growth}%")
    print(f"  PE 变化率：{burgess.pe_change}%")
    print(f"  建议：{burgess.signal.value} ({burgess.color.value})")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
