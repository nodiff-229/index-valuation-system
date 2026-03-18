# 指数基金估值表自动生成系统

每天 14:00 自动生成《指数基金估值数据分析表》Excel 文件，并通过飞书发送。

## 技术栈
- Python 3.14.3 (macOS Apple Silicon)
- AkShare (核心数据源，免费)
- pandas + openpyxl (Excel 生成)
- cron (定时任务)

## 快速开始

### 1. 安装依赖
```bash
cd ~/.openclaw/workspace/index_valuation_system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 测试运行（模拟数据）
```bash
ENABLE_MOCK_DATA=true python main.py --run-once --no-feishu
```

### 3. 配置飞书（可选）
编辑 `feishu_sender.py`，设置你的飞书应用凭证：
```python
FEISHU_APP_ID = "your_app_id"
FEISHU_APP_SECRET = "your_app_secret"
```

或使用环境变量：
```bash
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"
```

### 4. 配置定时任务
```bash
# 安装 cron 任务（每天 14:00 执行）
crontab cron.txt

# 验证
crontab -l
```

### 5. 手动运行
```bash
# 运行一次（使用真实数据）
python main.py --run-once

# 启动定时任务（后台运行）
python main.py --start-scheduler
```

## 输出
- Excel 文件：`~/.openclaw/workspace/Index_Valuation/Index_Valuation_YYYYMMDD.xlsx`
- 日志文件：`~/.openclaw/workspace/index_valuation_system/index_valuation.log`

## 估值逻辑（格雷厄姆策略）

| 条件 | 信号 | 颜色 |
|------|------|------|
| 盈利收益率 > 2×国债收益率 | 开始定投 | 绿色 |
| 国债收益率 < 盈利收益率 ≤ 2×国债收益率 | 继续持有 | 橙色 |
| 盈利收益率 ≤ 国债收益率 | 分批卖出 | 红色 |

**十年期国债收益率**：默认 1.83%（可通过 `--bond-yield` 参数调整）

## 支持的指数
- 中证红利 (000922.SH)
- 沪深 300 (000300.SH)
- 科创 50 (000688.SH)
- 纳斯达克 100

## 数据源说明
- **AkShare**：主要数据源，免费无需 API key
- **Tushare Pro**：备选数据源（需要有效 Token）
- **Mock 数据**：测试模式使用

## 命令行参数
```bash
python main.py --help

# 常用参数：
--run-once         # 手动运行一次
--start-scheduler  # 启动定时任务
--no-feishu        # 不发送飞书
--bond-yield 2.0   # 指定国债收益率
```

## 故障排查

### Tushare Token 失效
系统会自动切换到 AkShare 或 Mock 数据源，不影响运行。

### 飞书发送失败
检查 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 是否正确配置。

### 定时任务未执行
```bash
# 查看 cron 日志
grep CRON /var/log/system.log

# 验证 cron 任务
crontab -l
```

## 项目结构
```
index_valuation_system/
├── main.py              # 主入口
├── data_collector.py    # 数据收集模块
├── valuation_logic.py   # 估值分析模块
├── excel_generator.py   # Excel 生成模块
├── feishu_sender.py     # 飞书发送模块
├── run_daily.sh         # 每日执行脚本
├── cron.txt             # Cron 任务配置
├── requirements.txt     # Python 依赖
└── README.md            # 本文档
```
