"""
指数估值系统主入口

整合数据收集、估值分析、Excel 生成和飞书发送模块。
支持手动运行和定时调度两种模式。

使用方法:
    python main.py --run-once          # 手动运行一次
    python main.py --start-scheduler   # 启动定时任务（每天 14:00）
"""

import argparse
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import subprocess

# 导入各模块
from data_collector import DataCollector, IndexValuation, INDEX_CONFIG
from excel_generator import ExcelGenerator, IndexValuationData
from valuation_logic import ValuationLogic

# ============================================================================
# 日志配置
# ============================================================================

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 配置根日志
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent / "index_valuation.log",
            encoding="utf-8"
        )
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# 常量定义
# ============================================================================

# 十年期国债收益率（%）
DEFAULT_BOND_YIELD = 1.83

# 输出目录
OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "Index_Valuation"

# 定时任务时间 - 每天晚上 21:00
SCHEDULE_HOUR = 21
SCHEDULE_MINUTE = 0

# ============================================================================
# 全局变量
# ============================================================================

# 调度器实例
scheduler: Optional[BlockingScheduler] = None

# 是否正在运行
is_running = True


# ============================================================================
# 信号处理
# ============================================================================

def signal_handler(signum, frame):
    """处理退出信号，实现优雅退出"""
    global is_running, scheduler

    logger.info(f"收到退出信号 {signum}，正在优雅退出...")

    is_running = False

    if scheduler is not None:
        logger.info("正在关闭调度器...")
        scheduler.shutdown(wait=False)

    logger.info("程序已退出")
    sys.exit(0)


# 注册信号处理
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ============================================================================
# 核心业务逻辑
# ============================================================================

def run_valuation_workflow(
    bond_yield: float = DEFAULT_BOND_YIELD,
    send_to_feishu: bool = True
) -> Optional[Path]:
    """执行完整的估值分析流程

    流程步骤：
    1. 收集指数数据
    2. 计算估值分析
    3. 生成 Excel 报告
    4. 发送到飞书（可选）

    Args:
        bond_yield: 十年期国债收益率 (%)
        send_to_feishu: 是否发送到飞书

    Returns:
        生成的 Excel 文件路径，失败返回 None
    """
    logger.info("=" * 60)
    logger.info("开始执行指数估值分析流程")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    excel_path = None

    try:
        # --------------------------------------------------------------------
        # 第一步：收集数据
        # --------------------------------------------------------------------
        logger.info("\n[1/4] 正在收集指数数据...")

        collector = DataCollector()
        valuations = collector.get_all_index_valuations()

        if not valuations:
            logger.error("未能收集到任何指数数据，流程终止")
            return None

        logger.info(f"成功收集 {len(valuations)} 个指数的数据")

        # --------------------------------------------------------------------
        # 第二步：估值分析
        # --------------------------------------------------------------------
        logger.info("\n[2/4] 正在进行估值分析...")

        logic = ValuationLogic(bond_yield=bond_yield)
        generator = ExcelGenerator(output_dir=OUTPUT_DIR)  # 提前初始化用于博格公式计算
        analysis_results = []

        for code, valuation in valuations.items():
            try:
                # 获取历史数据用于百分位计算
                history_df = collector.get_index_pe_history(code)

                if history_df.empty:
                    logger.warning(f"{valuation.name} 历史数据为空，跳过分析")
                    continue

                # 执行估值分析
                analysis = logic.analyze(
                    pe=valuation.pe,
                    pb=valuation.pb,
                    pe_history=history_df["pe"],
                    pb_history=history_df["pb"],
                    dividend_yield=valuation.dividend_yield
                )

                # 获取指数类别
                category = INDEX_CONFIG.get(code, {}).get("category", "")
                
                # 计算博格公式建议
                historical_pe = analysis.pe_percentile.mean_value
                burgess_advice, burgess_color, expected_return = generator._calculate_burgess_advice(
                    category=category,
                    dividend_yield=analysis.dividend_yield,
                    pe=analysis.pe,
                    historical_pe=historical_pe,
                    roe=valuation.roe,
                    bond_yield=bond_yield
                )
                
                # 转换为 Excel 数据格式（包含博格公式）
                excel_data = IndexValuationData(
                    name=valuation.name,
                    pe=analysis.pe,
                    pb=analysis.pb,
                    dividend_yield=analysis.dividend_yield,
                    roe=valuation.roe,
                    earnings_yield=analysis.earnings_yield,
                    pe_percentile=analysis.pe_percentile.percentile,
                    pb_percentile=analysis.pb_percentile.percentile,
                    valuation_zone=analysis.combined_zone.value,
                    investment_advice=analysis.graham_signal.value,
                    burgess_advice=burgess_advice,
                    burgess_color=burgess_color,
                    category=category,
                    expected_return=expected_return,
                )

                analysis_results.append(excel_data)

                logger.info(
                    f"{valuation.name}: PE百分位={analysis.pe_percentile.percentile}%, "
                    f"区域={analysis.combined_zone.value}, "
                    f"建议={analysis.graham_signal.value}"
                )

            except Exception as e:
                logger.error(f"分析 {valuation.name} 时发生错误: {e}")
                continue

        if not analysis_results:
            logger.error("没有成功分析的指数，流程终止")
            return None

        logger.info(f"成功分析 {len(analysis_results)} 个指数")

        # --------------------------------------------------------------------
        # 第三步：生成 Excel 报告
        # --------------------------------------------------------------------
        logger.info("\n[3/4] 正在生成 Excel 报告...")

        excel_path = generator.generate(analysis_results, bond_yield=bond_yield)

        logger.info(f"Excel 报告已生成: {excel_path}")

        # --------------------------------------------------------------------
        # 第四步：发送到飞书
        # --------------------------------------------------------------------
        if send_to_feishu:
            logger.info("\n[4/4] 正在发送到飞书...")

            try:
                # 使用 subprocess 调用 send_via_openclaw.py 脚本
                script_path = Path(__file__).parent / "send_via_openclaw.py"
                result = subprocess.run(
                    [sys.executable, str(script_path), str(excel_path), "每日指数估值报告"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    logger.info("报告已成功发送到飞书")
                    logger.info(result.stdout.strip())
                else:
                    logger.error(f"发送到飞书失败: {result.stderr.strip()}")

            except subprocess.TimeoutExpired:
                logger.error("发送到飞书超时")
            except Exception as e:
                logger.error(f"发送到飞书时发生错误: {e}")
        else:
            logger.info("\n[4/4] 跳过飞书发送步骤")

        # --------------------------------------------------------------------
        # 完成
        # --------------------------------------------------------------------
        logger.info("\n" + "=" * 60)
        logger.info("指数估值分析流程完成")
        logger.info(f"报告路径: {excel_path}")
        logger.info("=" * 60)

        return excel_path

    except Exception as e:
        logger.error(f"执行估值分析流程时发生错误: {e}", exc_info=True)
        return None


def scheduled_job():
    """定时任务入口"""
    logger.info("\n" + "=" * 60)
    logger.info("定时任务触发")
    logger.info("=" * 60)

    try:
        run_valuation_workflow(
            bond_yield=DEFAULT_BOND_YIELD,
            send_to_feishu=True
        )
    except Exception as e:
        logger.error(f"定时任务执行失败: {e}", exc_info=True)


# ============================================================================
# 调度器管理
# ============================================================================

def start_scheduler():
    """启动定时调度器"""
    global scheduler

    logger.info("=" * 60)
    logger.info("启动定时调度器")
    logger.info(f"定时任务时间: 每天 {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}")
    logger.info("=" * 60)

    # 创建调度器
    scheduler = BlockingScheduler()

    # 添加定时任务（每天 14:00 执行）
    trigger = CronTrigger(
        hour=SCHEDULE_HOUR,
        minute=SCHEDULE_MINUTE
    )

    scheduler.add_job(
        scheduled_job,
        trigger=trigger,
        id="index_valuation_daily",
        name="指数估值日报",
        misfire_grace_time=3600  # 允许1小时内的误触
    )

    logger.info("调度器已启动，按 Ctrl+C 退出")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("收到退出信号，正在关闭调度器...")
        scheduler.shutdown(wait=False)
        logger.info("调度器已关闭")


# ============================================================================
# 命令行接口
# ============================================================================

def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="指数估值系统 - 自动收集指数数据并生成估值报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python main.py --run-once          # 手动运行一次
    python main.py --start-scheduler   # 启动定时任务（每天 14:00）

环境变量:
    FEISHU_APP_ID      飞书应用 ID（发送报告需要）
    FEISHU_APP_SECRET  飞书应用密钥（发送报告需要）
    FEISHU_CHAT_ID     飞书群组 ID（可选，使用默认群组）
        """
    )

    # 互斥参数组：只能选择其中一个
    mode_group = parser.add_mutually_exclusive_group(required=True)

    mode_group.add_argument(
        "--run-once",
        action="store_true",
        help="手动运行一次分析流程"
    )

    mode_group.add_argument(
        "--start-scheduler",
        action="store_true",
        help="启动定时调度器（每天 14:00 运行）"
    )

    # 可选参数
    parser.add_argument(
        "--bond-yield",
        type=float,
        default=DEFAULT_BOND_YIELD,
        help=f"十年期国债收益率（%%），默认 {DEFAULT_BOND_YIELD}"
    )

    parser.add_argument(
        "--no-feishu",
        action="store_true",
        help="不发送到飞书（仅生成报告）"
    )

    return parser.parse_args()


def main():
    """主入口"""
    # 解析命令行参数
    args = parse_args()

    logger.info("=" * 60)
    logger.info("指数估值系统启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"输出目录: {OUTPUT_DIR}")
    logger.info("=" * 60)

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if args.run_once:
            # 手动运行一次
            logger.info("运行模式: 单次执行")

            result = run_valuation_workflow(
                bond_yield=args.bond_yield,
                send_to_feishu=not args.no_feishu
            )

            if result:
                logger.info(f"执行成功，报告路径: {result}")
                sys.exit(0)
            else:
                logger.error("执行失败")
                sys.exit(1)

        elif args.start_scheduler:
            # 启动定时调度器
            logger.info("运行模式: 定时调度")

            start_scheduler()

    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()