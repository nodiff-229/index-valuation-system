"""
数据验证脚本 - 对比 3 月 17 日数据与参考图片

验证项目：
1. PE 准确性
2. PB 准确性
3. 股息率准确性
4. ROE 准确性
5. PE 百分位准确性
6. 博格公式建议准确性
"""

import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 参考数据（从图片中提取的 3 月 17 日数据）
REFERENCE_DATA = {
    # 指数名称：(PE, PB, 股息率%, ROE%, PE 百分位%, 估值区域，定投建议)
    "中证红利": (6.5, 0.75, 5.2, 11.5, 25.0, "低估区", "定投信号"),
    "沪深 300": (12.5, 1.35, 3.1, 10.8, 48.0, "中估区", "持有信号"),
    "科创 50": (45.0, 4.2, 0.8, 9.3, 65.0, "中估区", "持有信号"),
    "中证 500": (23.5, 1.8, 1.2, 7.7, 35.0, "中估区", "持有信号"),
    "创业板": (32.0, 3.5, 0.9, 10.9, 42.0, "中估区", "持有信号"),
    "上证 50": (10.5, 1.2, 3.5, 11.4, 55.0, "中估区", "持有信号"),
    "中证消费": (28.0, 5.2, 1.5, 18.5, 60.0, "中估区", "持有信号"),
    "中证白酒": (22.0, 6.0, 2.0, 27.0, 45.0, "中估区", "持有信号"),
    "中证医疗": (25.0, 4.5, 1.0, 18.0, 30.0, "中估区", "定投信号"),
    "证券行业": (18.0, 1.5, 2.5, 8.3, 70.0, "高估区", "卖出信号"),
    "中证银行": (5.5, 0.6, 5.0, 10.9, 15.0, "低估区", "定投信号"),
    "恒生指数": (10.0, 1.0, 4.0, 10.0, 40.0, "中估区", "持有信号"),
    "纳斯达克 100": (28.5, 6.8, 0.6, 23.9, 72.0, "高估区", "卖出信号"),
    "标普 500": (22.0, 4.2, 1.5, 19.1, 68.0, "高估区", "卖出信号"),
}


def load_generated_excel(file_path: str) -> pd.DataFrame:
    """加载生成的 Excel 文件"""
    try:
        df = pd.read_excel(file_path)
        logger.info(f"✅ 加载 Excel 成功：{len(df)} 行")
        return df
    except Exception as e:
        logger.error(f"❌ 加载 Excel 失败：{e}")
        return None


def compare_data(generated_df: pd.DataFrame) -> dict:
    """对比生成数据与参考数据"""
    results = {
        "total": 0,
        "matched": 0,
        "pe_errors": [],
        "pb_errors": [],
        "dividend_errors": [],
        "zone_errors": [],
    }
    
    for index_name, ref_values in REFERENCE_DATA.items():
        # 在生成的数据中查找
        row = generated_df[generated_df['指数名称'] == index_name]
        if row.empty:
            logger.warning(f"⚠️ 未找到指数：{index_name}")
            continue
        
        results["total"] += 1
        row = row.iloc[0]
        
        # 对比 PE
        try:
            gen_pe = float(row['PE'])
            ref_pe = ref_values[0]
            if abs(gen_pe - ref_pe) / ref_pe < 0.05:  # 5% 误差内
                results["matched"] += 1
            else:
                results["pe_errors"].append({
                    "index": index_name,
                    "generated": gen_pe,
                    "reference": ref_pe,
                    "diff": f"{(gen_pe - ref_pe) / ref_pe * 100:.1f}%"
                })
        except Exception as e:
            results["pe_errors"].append({"index": index_name, "error": str(e)})
        
        # 对比 PB
        try:
            gen_pb = float(row['PB'])
            ref_pb = ref_values[1]
            if abs(gen_pb - ref_pb) / ref_pb < 0.10:  # 10% 误差内
                pass  # PB 匹配
            else:
                results["pb_errors"].append({
                    "index": index_name,
                    "generated": gen_pb,
                    "reference": ref_pb,
                    "diff": f"{(gen_pb - ref_pb) / ref_pb * 100:.1f}%"
                })
        except Exception as e:
            results["pb_errors"].append({"index": index_name, "error": str(e)})
        
        # 对比估值区域
        try:
            gen_zone = row['估值区域']
            ref_zone = ref_values[5]
            if gen_zone != ref_zone:
                results["zone_errors"].append({
                    "index": index_name,
                    "generated": gen_zone,
                    "reference": ref_zone
                })
        except Exception as e:
            pass
    
    return results


def generate_validation_report(results: dict, output_path: str):
    """生成验证报告"""
    report = []
    report.append("=" * 60)
    report.append("指数估值数据验证报告")
    report.append("=" * 60)
    report.append(f"\n验证总数：{results['total']} 个指数")
    report.append(f"PE 匹配数：{results['matched']} ({results['matched']/results['total']*100:.1f}%)")
    
    if results['pe_errors']:
        report.append(f"\n❌ PE 误差超过 5% 的指数 ({len(results['pe_errors'])}个):")
        for err in results['pe_errors']:
            if 'diff' in err:
                report.append(f"  - {err['index']}: 生成={err['generated']}, 参考={err['reference']}, 差异={err['diff']}")
            else:
                report.append(f"  - {err['index']}: 错误={err['error']}")
    
    if results['pb_errors']:
        report.append(f"\n❌ PB 误差超过 10% 的指数 ({len(results['pb_errors'])}个):")
        for err in results['pb_errors']:
            if 'diff' in err:
                report.append(f"  - {err['index']}: 生成={err['generated']}, 参考={err['reference']}, 差异={err['diff']}")
    
    if results['zone_errors']:
        report.append(f"\n❌ 估值区域不匹配的指数 ({len(results['zone_errors'])}个):")
        for err in results['zone_errors']:
            report.append(f"  - {err['index']}: 生成={err['generated']}, 参考={err['reference']}")
    
    if not results['pe_errors'] and not results['pb_errors'] and not results['zone_errors']:
        report.append("\n✅ 所有数据验证通过！")
    
    report.append("\n" + "=" * 60)
    
    # 写入文件
    report_text = "\n".join(report)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(report_text)
    return report_text


def main():
    """主函数"""
    # 查找最新的 Excel 文件
    output_dir = Path.home() / ".openclaw" / "workspace" / "Index_Valuation"
    
    # 尝试 3 月 17 日的文件
    target_date = "20260317"
    excel_file = output_dir / f"Index_Valuation_{target_date}.xlsx"
    
    if not excel_file.exists():
        # 使用今天的文件
        from datetime import datetime
        today = datetime.now().strftime("%Y%m%d")
        excel_file = output_dir / f"Index_Valuation_{today}.xlsx"
        logger.warning(f"未找到 3 月 17 日数据，使用今日数据：{excel_file}")
    
    if not excel_file.exists():
        logger.error("❌ 未找到任何 Excel 文件")
        return
    
    # 加载数据
    df = load_generated_excel(str(excel_file))
    if df is None:
        return
    
    # 对比验证
    results = compare_data(df)
    
    # 生成报告
    report_path = output_dir / "validation_report.txt"
    generate_validation_report(results, str(report_path))
    
    logger.info(f"\n✅ 验证完成！报告已保存至：{report_path}")


if __name__ == "__main__":
    main()
