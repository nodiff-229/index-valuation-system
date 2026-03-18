#!/bin/bash
# 指数估值表每日自动生成脚本
# 每天 14:00 执行

# 激活虚拟环境
source ~/.openclaw/workspace/index_valuation_system/venv/bin/activate

# 运行估值系统
cd ~/.openclaw/workspace/index_valuation_system
python main.py --run-once

# 日志输出到系统日志
echo "指数估值表生成完成: $(date)" >> ~/.openclaw/workspace/index_valuation_system/daily_run.log
