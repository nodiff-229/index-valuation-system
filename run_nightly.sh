#!/bin/bash
# 指数估值系统 - 定时运行脚本（每晚 22:00）
# 用于获取 Tushare 更新后的完整估值数据

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f ~/.openclaw/.env ]; then
    source ~/.openclaw/.env
fi

# 激活虚拟环境
source venv/bin/activate

# 记录日志
echo "========================================" >> index_valuation.log
echo "运行时间：$(date '+%Y-%m-%d %H:%M:%S')" >> index_valuation.log
echo "========================================" >> index_valuation.log

# 运行估值系统
python main.py --run-once 2>&1 | tee -a index_valuation.log

# 检查是否生成文件
if [ -f "../Index_Valuation/Index_Valuation_$(date +%Y%m%d).xlsx" ]; then
    echo "✅ Excel 生成成功" >> index_valuation.log
    
    # 发送到飞书
    python send_via_openclaw.py 2>&1 | tee -a index_valuation.log
else
    echo "❌ Excel 生成失败" >> index_valuation.log
fi

echo "运行完成" >> index_valuation.log
