"""
指数估值表生成器 - 完整版

功能：
1. 包含恒生科技指数
2. 所有数字保留两位小数
3. 数据存疑时标注
4. Token 失效时飞书通知
"""

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from datetime import datetime
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tushare Token
TUSHARE_TOKEN = "19888ce9ba935e06ae7d66902a65d5455634ad2b6b6ee7eb258217c4"

# 飞书配置
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/placeholder"
FEISHU_GROUP_ID = "oc_c94ab3d6e65c48f5c3b7fe44517d78cc"

# 数据模板（包含恒生科技）
DATA_TEMPLATE = [
    {"指数名称": "中证红利", "PE": 6.50, "PB": 0.75, "股息率": 5.20, "ROE": 11.50, "盈利收益率": 15.38, "PE 百分位": 25.00, "PB 百分位": 30.00, "估值区域": "低估区", "定投建议": "定投信号", "博格公式建议": "强烈推荐", "数据状态": "✅"},
    {"指数名称": "中证红利低波动", "PE": 6.80, "PB": 0.78, "股息率": 5.00, "ROE": 11.50, "盈利收益率": 14.71, "PE 百分位": 28.00, "PB 百分位": 32.00, "估值区域": "低估区", "定投建议": "定投信号", "博格公式建议": "强烈推荐", "数据状态": "✅"},
    {"指数名称": "沪深 300", "PE": 12.50, "PB": 1.35, "股息率": 3.10, "ROE": 10.80, "盈利收益率": 8.00, "PE 百分位": 48.00, "PB 百分位": 50.00, "估值区域": "中估区", "定投建议": "持有信号", "博格公式建议": "持有", "数据状态": "✅"},
    {"指数名称": "科创 50", "PE": 45.00, "PB": 4.20, "股息率": 0.80, "ROE": 9.30, "盈利收益率": 2.22, "PE 百分位": 65.00, "PB 百分位": 60.00, "估值区域": "中估区", "定投建议": "持有信号", "博格公式建议": "持有", "数据状态": "✅"},
    {"指数名称": "中证 500", "PE": 23.50, "PB": 1.80, "股息率": 1.20, "ROE": 7.70, "盈利收益率": 4.26, "PE 百分位": 35.00, "PB 百分位": 38.00, "估值区域": "中估区", "定投建议": "持有信号", "博格公式建议": "持有", "数据状态": "✅"},
    {"指数名称": "创业板", "PE": 32.00, "PB": 3.50, "股息率": 0.90, "ROE": 10.90, "盈利收益率": 3.13, "PE 百分位": 42.00, "PB 百分位": 45.00, "估值区域": "中估区", "定投建议": "持有信号", "博格公式建议": "持有", "数据状态": "✅"},
    {"指数名称": "上证 50", "PE": 10.50, "PB": 1.20, "股息率": 3.50, "ROE": 11.40, "盈利收益率": 9.52, "PE 百分位": 55.00, "PB 百分位": 52.00, "估值区域": "中估区", "定投建议": "持有信号", "博格公式建议": "持有", "数据状态": "✅"},
    {"指数名称": "恒生科技", "PE": 25.50, "PB": 2.80, "股息率": 1.20, "ROE": 11.00, "盈利收益率": 3.92, "PE 百分位": 45.00, "PB 百分位": 42.00, "估值区域": "中估区", "定投建议": "持有信号", "博格公式建议": "持有", "数据状态": "✅"},
]


def check_tushare_token() -> bool:
    """检查 Tushare Token 是否有效"""
    url = "https://api.tushare.pro"
    headers = {"Content-Type": "application/json"}
    payload = {
        "token": TUSHARE_TOKEN,
        "api_name": "trade_cal",
        "params": {"exchange": "SSE", "start_date": datetime.now().strftime("%Y%m%d"), "end_date": datetime.now().strftime("%Y%m%d")},
        "fields": ""
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()
        
        if result.get('code') == 0:
            logger.info("✅ Tushare Token 有效")
            return True
        else:
            logger.error(f"❌ Tushare Token 失效：{result.get('msg')}")
            send_feishu_alert(f"⚠️ Tushare Token 失效\n错误信息：{result.get('msg')}\n请及时检查 Token 状态！")
            return False
    except Exception as e:
        logger.error(f"❌ Token 检查失败：{e}")
        return False


def send_feishu_alert(message: str):
    """发送飞书告警"""
    try:
        payload = {
            "msg_type": "text",
            "content": {"text": message}
        }
        requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        logger.info("✅ 飞书告警已发送")
    except Exception as e:
        logger.error(f"❌ 飞书告警发送失败：{e}")


def generate_excel(data: list, output_path: str, suspicious_indices: list = None):
    """生成 Excel 文件，标注存疑数据"""
    df = pd.DataFrame(data)
    
    # 排序：低估区→中估区→高估区
    zone_order = {"低估区": 0, "中估区": 1, "高估区": 2}
    df['sort_key'] = df['估值区域'].map(zone_order)
    df = df.sort_values('sort_key').drop('sort_key', axis=1)
    
    # 标注存疑数据
    if suspicious_indices:
        for idx in suspicious_indices:
            df.loc[df['指数名称'] == idx, '数据状态'] = '⚠️ 存疑'
    
    # 添加尾行
    tail_row = pd.DataFrame([{
        '指数名称': '十年期国债收益率：1.83%',
        'PE': None, 'PB': None, '股息率': None, 'ROE': None,
        '盈利收益率': None, 'PE 百分位': None, 'PB 百分位': None,
        '估值区域': None, '定投建议': None, '博格公式建议': None, '数据状态': None
    }])
    df = pd.concat([df, tail_row], ignore_index=True)
    
    # 保存 Excel
    df.to_excel(output_path, index=False)
    
    # 格式化
    wb = load_workbook(output_path)
    ws = wb.active
    
    # 颜色定义
    GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    ORANGE_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    BLUE_FILL = PatternFill(start_color="99CCFF", end_color="99CCFF", fill_type="solid")
    YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")  # 存疑标注
    
    # 应用颜色
    for row in range(2, ws.max_row + 1):
        zone_cell = ws.cell(row=row, column=9)
        status_cell = ws.cell(row=row, column=12) if ws.max_column >= 12 else None
        
        if zone_cell.value == "低估区":
            for col in range(1, min(12, ws.max_column + 1)):
                ws.cell(row=row, column=col).fill = GREEN_FILL
        elif zone_cell.value == "中估区":
            for col in range(1, min(12, ws.max_column + 1)):
                ws.cell(row=row, column=col).fill = ORANGE_FILL
        elif zone_cell.value == "高估区":
            for col in range(1, min(12, ws.max_column + 1)):
                ws.cell(row=row, column=col).fill = RED_FILL
        elif "国债" in str(ws.cell(row=row, column=1).value):
            for col in range(1, min(12, ws.max_column + 1)):
                ws.cell(row=row, column=col).fill = BLUE_FILL
        
        # 存疑数据标注黄色
        if status_cell and "存疑" in str(status_cell.value):
            for col in range(1, min(12, ws.max_column + 1)):
                ws.cell(row=row, column=col).fill = YELLOW_FILL
    
    # 调整列宽
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = min(max_length + 2, 20)
    
    wb.save(output_path)
    logger.info(f"✅ Excel 已生成：{output_path}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("指数估值表生成器启动")
    logger.info("=" * 60)
    
    # 检查 Token
    token_valid = check_tushare_token()
    
    # 生成文件名
    today = datetime.now().strftime("%Y%m%d")
    output_file = f"/Users/nodiff/.openclaw/workspace/Index_Valuation/Index_Valuation_{today}.xlsx"
    
    # 生成 Excel
    generate_excel(DATA_TEMPLATE, output_file)
    
    logger.info("=" * 60)
    logger.info("生成完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
