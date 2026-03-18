#!/bin/bash
# 指数估值表 - 每日定时运行（21:00）
# 功能：获取数据、生成 Excel、飞书发送、异常告警

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f ~/.openclaw/.env ]; then
    source ~/.openclaw/.env
fi

# 激活虚拟环境
source venv/bin/activate

# 日志
LOG_FILE="$SCRIPT_DIR/index_valuation.log"
echo "========================================" >> "$LOG_FILE"
echo "运行时间：$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 运行生成器
python generate_valuation_table.py 2>&1 | tee -a "$LOG_FILE"

# 检查是否生成文件
TODAY=$(date +%Y%m%d)
OUTPUT_FILE="../Index_Valuation/Index_Valuation_${TODAY}.xlsx"

if [ -f "$OUTPUT_FILE" ]; then
    echo "✅ Excel 生成成功：$OUTPUT_FILE" >> "$LOG_FILE"
    
    # 发送到飞书
    python send_via_openclaw.py 2>&1 | tee -a "$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ 飞书发送成功" >> "$LOG_FILE"
    else
        echo "❌ 飞书发送失败" >> "$LOG_FILE"
    fi
else
    echo "❌ Excel 生成失败" >> "$LOG_FILE"
    # 发送告警
    python -c "
import requests
msg = '❌ 指数估值表生成失败\n时间：$(date)'\nrequests.post('$FEISHU_WEBHOOK', json={'msg_type': 'text', 'content': {'text': msg}}, timeout=10)
" 2>&1 | tee -a "$LOG_FILE"
fi

echo "运行完成" >> "$LOG_FILE"
