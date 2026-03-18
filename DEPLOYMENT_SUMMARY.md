# 指数基金估值表系统 - 部署完成

## ✅ 完成状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 数据采集 | ✅ | AkShare 为主，Tushare 备选，Mock 数据 fallback |
| 估值逻辑 | ✅ | 格雷厄姆策略 + 历史百分位 |
| Excel 生成 | ✅ | 彩色分区，自动排序 |
| 飞书发送 | ✅ | 通过 OpenClaw message 工具 |
| 定时任务 | ✅ | cron 每天 14:00 执行 |

## 📁 项目结构

```
~/.openclaw/workspace/index_valuation_system/
├── main.py              # 主入口
├── data_collector.py    # 数据采集（AkShare 优先）
├── valuation_logic.py   # 估值分析（格雷厄姆策略）
├── excel_generator.py   # Excel 生成（彩色分区）
├── feishu_sender.py     # 飞书发送（备用）
├── send_via_openclaw.py # OpenClaw message 封装
├── run_daily.sh         # 每日执行脚本
├── cron.txt             # Cron 配置
├── requirements.txt     # Python 依赖
├── README.md            # 使用说明
├── FEISHU_CONFIG.md     # 飞书配置指南
└── venv/                # Python 虚拟环境
```

## 🚀 快速使用

### 手动运行（测试模式）
```bash
cd ~/.openclaw/workspace/index_valuation_system
source venv/bin/activate
ENABLE_MOCK_DATA=true python main.py --run-once
```

### 手动运行（真实数据）
```bash
python main.py --run-once
```

### 安装定时任务
```bash
# 查看当前 cron
crontab -l

# 安装定时任务（每天 14:00）
crontab cron.txt

# 验证
crontab -l
```

## 📊 输出示例

生成的 Excel 包含：
- **指数名称**：中证红利、沪深 300、科创 50、纳斯达克 100
- **估值指标**：PE、PB、股息率、ROE、盈利收益率
- **历史百分位**：PE/PB 过去 10 年百分位
- **估值区域**：低估区（绿色）、中估区（橙色）、高估区（红色）
- **定投建议**：开始定投、继续持有、分批卖出

## 🎯 格雷厄姆策略

| 条件 | 信号 | 颜色 |
|------|------|------|
| 盈利收益率 > 2×国债收益率 | 开始定投 | 🟢 绿色 |
| 国债收益率 < 盈利收益率 ≤ 2×国债收益率 | 继续持有 | 🟠 橙色 |
| 盈利收益率 ≤ 国债收益率 | 分批卖出 | 🔴 红色 |

**十年期国债收益率**：默认 1.83%

## 📝 注意事项

1. **数据源**：优先使用 AkShare（免费），Tushare Token 已失效
2. **飞书发送**：通过 OpenClaw message 工具，无需额外配置
3. **定时任务**：需要 macOS 允许 cron 访问权限
4. **日志查看**：`index_valuation.log`

## 🔧 故障排查

### AkShare 接口失效
系统自动 fallback 到 Mock 数据（测试模式）

### 飞书发送失败
检查 OpenClaw 环境是否正常：
```bash
openclaw message send --help
```

### Cron 未执行
```bash
# 检查 cron 权限
sudo systempreferences.securityprivacy.privacy.automation

# 查看 cron 日志
log show --predicate 'process == "cron"' --last 1h
```

## 📈 下一步优化

1. 增加更多指数（中证 500、创业板等）
2. 添加数据可视化图表到 Excel
3. 支持自定义指数配置
4. 添加估值趋势历史记录

---

**部署时间**：2026-03-18  
**部署位置**：`~/.openclaw/workspace/index_valuation_system/`  
**测试状态**：✅ 通过（模拟数据 + 飞书发送）
