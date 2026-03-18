# 指数基金估值表 - 部署指南

## ✅ 系统已就绪

**项目位置**: `~/.openclaw/workspace/index_valuation_system/`  
**输出目录**: `~/.openclaw/workspace/Index_Valuation/`

## 当前状态

- ✅ 数据采集模块：使用模拟数据（真实 API 需配置）
- ✅ 估值逻辑模块：格雷厄姆策略已实现
- ✅ Excel 生成模块：颜色区分、排序已完成
- ✅ 定时任务：待配置
- ✅ 飞书通知：待配置

## 快速开始

### 1. 手动运行一次

```bash
cd ~/.openclaw/workspace/index_valuation_system
source venv/bin/activate
python main.py --run-once
```

### 2. 配置定时任务（每天 14:00）

**方式 A: 使用 cron**
```bash
crontab ~/.openclaw/workspace/index_valuation_system/cron.txt
```

**方式 B: 使用 macOS Launchd**
```bash
# 创建 launchd 配置文件
cat > ~/Library/LaunchAgents/com.index.valuation.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.index.valuation</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/nodiff/.openclaw/workspace/index_valuation_system/run_daily.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>14</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/Users/nodiff/.openclaw/workspace/index_valuation_system</string>
    <key>StandardOutPath</key>
    <string>/Users/nodiff/.openclaw/workspace/index_valuation_system/index_valuation.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/nodiff/.openclaw/workspace/index_valuation_system/index_valuation_error.log</string>
</dict>
</plist>
EOF

# 加载配置
launchctl load ~/Library/LaunchAgents/com.index.valuation.plist
```

### 3. 配置飞书通知（可选）

编辑 `~/.openclaw/.env`:
```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxx
FEISHU_GROUP_ID=oc_c94ab3d6e65c48f5c3b7fe44517d78cc
```

## 输出文件

**文件名**: `Index_Valuation_YYYYMMDD.xlsx`  
**位置**: `~/.openclaw/workspace/Index_Valuation/`

**表格内容**:
- 指数名称、PE、PB、股息率、ROE、盈利收益率
- PE 百分位、PB 百分位（基于 10 年历史）
- 估值区域（低估/中估/高估）
- 格雷厄姆策略建议（定投/持有/卖出）

**格式**:
- 低估区（绿色）：百分位 < 30%
- 中估区（橙色）：百分位 30%-70%
- 高估区（红色）：百分位 > 70%
- 尾行：十年期国债收益率（蓝色）

## 数据源配置（生产环境）

### Tushare Pro
1. 注册 https://tushare.pro
2. 获取 Token
3. 编辑 `data_collector.py`，替换 `TUSHARE_TOKEN`

### 真实数据测试
```bash
# 禁用模拟数据
export ENABLE_MOCK_DATA=false
python main.py --run-once
```

## 故障排查

### 查看日志
```bash
tail -f ~/.openclaw/workspace/index_valuation_system/index_valuation.log
```

### 检查定时任务
```bash
# cron
crontab -l

# launchd
launchctl list | grep valuation
```

## 示例输出

```
指数名称    PE    PB   股息率   ROE     盈利收益率   PE 百分位  估值区域  定投建议
中证红利   6.5  0.75  5.2%  11.5%   15.38%    25%     低估区   定投信号
沪深 300  12.5  1.35  3.1%  10.8%    8.0%    48%     中估区   持有信号
科创 50   45.0  4.20  0.8%   9.3%    2.2%    65%     中估区   持有信号
纳指 100  28.5  6.80  0.6%  23.9%    3.5%    72%     高估区   卖出信号
```

---

**最后更新**: 2026-03-18
