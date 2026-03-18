# 飞书配置指南

## 获取飞书应用凭证

### 方法 1：使用现有 OpenClaw 飞书应用
如果 OpenClaw 已经配置了飞书集成，可以复用现有凭证。

检查 `~/.openclaw/.env` 文件：
```bash
cat ~/.openclaw/.env | grep FEISHU
```

### 方法 2：创建新的飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 创建企业自建应用
3. 获取凭证：
   - App ID
   - App Secret
4. 配置权限：
   - 发送消息
   - 上传文件
5. 发布应用

## 配置凭证

### 方式 A：环境变量（推荐）
编辑 `~/.openclaw/.env`：
```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxx
```

### 方式 B：直接修改代码
编辑 `feishu_sender.py`，修改：
```python
FEISHU_APP_ID = "cli_xxxxxxxxxxxxx"
FEISHU_APP_SECRET = "xxxxxxxxxxxxxxxxx"
```

## 测试发送

```bash
cd ~/.openclaw/workspace/index_valuation_system
source venv/bin/activate

# 测试发送（需要先配置凭证）
python main.py --run-once
```

## 目标群组
- 群组 ID：`oc_c94ab3d6e65c48f5c3b7fe44517d78cc`（Agent 小队）

## 常见问题

### 权限不足
确保飞书应用已添加以下权限：
- 发送消息到群组
- 上传文件

### Token 过期
飞书 tenant_access_token 有效期为 2 小时，系统会自动刷新。
