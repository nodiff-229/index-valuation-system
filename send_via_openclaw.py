#!/usr/bin/env python3
"""
使用 OpenClaw message 工具发送文件到飞书

此脚本通过调用 OpenClaw 的 message 工具发送 Excel 文件到飞书群组。
"""

import subprocess
import sys
from pathlib import Path


def send_to_feishu(file_path: str, title: str = "指数基金估值表") -> bool:
    """
    发送文件到飞书群组
    
    Args:
        file_path: Excel 文件路径
        title: 消息标题
    
    Returns:
        bool: 发送是否成功
    """
    # 飞书群组 ID
    chat_id = "oc_c94ab3d6e65c48f5c3b7fe44517d78cc"
    
    # 构建消息内容
    message = f"""📊 {title}

自动生成时间：{Path(file_path).stem.replace('Index_Valuation_', '')}

估值表已生成，请查收附件。

---
*格雷厄姆策略说明:*
🟢 盈利收益率 > 2×国债收益率 → 开始定投
🟠 国债收益率 < 盈利收益率 ≤ 2×国债收益率 → 继续持有
🔴 盈利收益率 ≤ 国债收益率 → 分批卖出
"""
    
    # 使用 OpenClaw message 工具发送
    # 注意：这需要在 OpenClaw 环境中运行
    try:
        cmd = [
            "openclaw",
            "message",
            "send",
            "--target", chat_id,
            "--message", message,
            "--media", file_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✓ 文件已发送到飞书群组：{chat_id}")
            return True
        else:
            print(f"✗ 发送失败：{result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ 发送超时")
        return False
    except FileNotFoundError:
        print("✗ 未找到 openclaw 命令，请确保在 OpenClaw 环境中运行")
        return False
    except Exception as e:
        print(f"✗ 发送错误：{e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python send_via_openclaw.py <excel 文件路径> [标题]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else "指数基金估值表"
    
    if not Path(file_path).exists():
        print(f"✗ 文件不存在：{file_path}")
        sys.exit(1)
    
    success = send_to_feishu(file_path, title)
    sys.exit(0 if success else 1)
