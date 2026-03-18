"""
飞书消息发送模块

通过飞书开放平台 API 发送消息和文件到飞书群组。
支持发送文本消息和文件附件。
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 常量定义
# ============================================================================

# 飞书 API 端点
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

# API 路径
TOKEN_API = "/auth/v3/tenant_access_token/internal"
UPLOAD_FILE_API = "/im/v1/files"
SEND_MESSAGE_API = "/im/v1/messages"

# 默认群组 ID
DEFAULT_CHAT_ID = "oc_c94ab3d6e65c48f5c3b7fe44517d78cc"

# 文件类型映射
FILE_TYPE_MAP = {
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".pdf": "pdf",
    ".doc": "doc",
    ".docx": "docx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
}


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class FeishuConfig:
    """飞书配置"""
    app_id: str
    app_secret: str
    chat_id: str = DEFAULT_CHAT_ID


@dataclass
class SendResult:
    """发送结果"""
    success: bool
    message: str
    message_id: Optional[str] = None
    file_key: Optional[str] = None


# ============================================================================
# 飞书发送器类
# ============================================================================

class FeishuSender:
    """飞书消息发送器

    支持功能：
    - 获取 tenant_access_token
    - 上传文件
    - 发送文本消息
    - 发送文件消息
    """

    def __init__(self, app_id: str, app_secret: str, chat_id: str = DEFAULT_CHAT_ID):
        """初始化飞书发送器

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
            chat_id: 群组 ID，默认使用配置的群组
        """
        self.config = FeishuConfig(
            app_id=app_id,
            app_secret=app_secret,
            chat_id=chat_id
        )
        self._token: Optional[str] = None
        self._token_expire_time: Optional[int] = None
        logger.info(f"飞书发送器初始化完成，群组 ID: {chat_id}")

    def _get_headers(self, with_token: bool = True) -> dict:
        """获取请求头

        Args:
            with_token: 是否包含 Authorization

        Returns:
            请求头字典
        """
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if with_token and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def get_tenant_access_token(self) -> bool:
        """获取 tenant_access_token

        Returns:
            是否成功获取 token
        """
        url = f"{FEISHU_API_BASE}{TOKEN_API}"

        payload = {
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret
        }

        try:
            logger.info("正在获取 tenant_access_token...")
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("msg", "未知错误")
                logger.error(f"获取 token 失败: {error_msg}")
                return False

            self._token = data.get("tenant_access_token")
            self._token_expire_time = data.get("expire")

            logger.info("tenant_access_token 获取成功")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"获取 token 请求失败: {e}")
            return False
        except Exception as e:
            logger.error(f"获取 token 发生异常: {e}")
            return False

    def _ensure_token(self) -> bool:
        """确保 token 有效

        Returns:
            token 是否有效
        """
        if self._token is None:
            return self.get_tenant_access_token()

        # 检查是否即将过期（提前 5 分钟刷新）
        if self._token_expire_time:
            current_time = int(datetime.now().timestamp())
            if current_time >= self._token_expire_time - 300:
                logger.info("token 即将过期，正在刷新...")
                return self.get_tenant_access_token()

        return True

    def upload_file(self, file_path: Path) -> Optional[str]:
        """上传文件到飞书

        Args:
            file_path: 文件路径

        Returns:
            file_key，失败返回 None
        """
        if not self._ensure_token():
            logger.error("token 无效，无法上传文件")
            return None

        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return None

        # 获取文件类型
        file_ext = file_path.suffix.lower()
        file_type = FILE_TYPE_MAP.get(file_ext, "stream")

        url = f"{FEISHU_API_BASE}{UPLOAD_FILE_API}"

        headers = {
            "Authorization": f"Bearer {self._token}"
        }

        try:
            with open(file_path, "rb") as f:
                files = {
                    "file": (file_path.name, f),
                    "file_type": (None, file_type),
                    "file_name": (None, file_path.name),
                }

                logger.info(f"正在上传文件: {file_path.name}")
                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    timeout=60
                )
                response.raise_for_status()

                data = response.json()

                if data.get("code") != 0:
                    error_msg = data.get("msg", "未知错误")
                    logger.error(f"上传文件失败: {error_msg}")
                    return None

                file_key = data.get("data", {}).get("file_key")
                logger.info(f"文件上传成功，file_key: {file_key}")
                return file_key

        except requests.exceptions.RequestException as e:
            logger.error(f"上传文件请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"上传文件发生异常: {e}")
            return None

    def send_text_message(
        self,
        text: str,
        chat_id: Optional[str] = None
    ) -> SendResult:
        """发送文本消息

        Args:
            text: 文本内容
            chat_id: 群组 ID，默认使用配置的群组

        Returns:
            SendResult 对象
        """
        if not self._ensure_token():
            return SendResult(
                success=False,
                message="token 无效，无法发送消息"
            )

        target_chat_id = chat_id or self.config.chat_id
        url = f"{FEISHU_API_BASE}{SEND_MESSAGE_API}"

        params = {
            "receive_id_type": "chat_id"
        }

        payload = {
            "receive_id": target_chat_id,
            "msg_type": "text",
            "content": f'{{"text":"{text}"}}'
        }

        try:
            logger.info(f"正在发送文本消息到群组: {target_chat_id}")
            response = requests.post(
                url,
                params=params,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("msg", "未知错误")
                logger.error(f"发送文本消息失败: {error_msg}")
                return SendResult(
                    success=False,
                    message=f"发送失败: {error_msg}"
                )

            message_id = data.get("data", {}).get("message_id")
            logger.info(f"文本消息发送成功，message_id: {message_id}")

            return SendResult(
                success=True,
                message="发送成功",
                message_id=message_id
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"发送文本消息请求失败: {e}")
            return SendResult(
                success=False,
                message=f"请求失败: {e}"
            )
        except Exception as e:
            logger.error(f"发送文本消息发生异常: {e}")
            return SendResult(
                success=False,
                message=f"发生异常: {e}"
            )

    def send_file_message(
        self,
        file_path: Path,
        text: Optional[str] = None,
        chat_id: Optional[str] = None
    ) -> SendResult:
        """发送文件消息

        Args:
            file_path: 文件路径
            text: 附加文本说明（可选）
            chat_id: 群组 ID，默认使用配置的群组

        Returns:
            SendResult 对象
        """
        # 上传文件
        file_key = self.upload_file(file_path)
        if not file_key:
            return SendResult(
                success=False,
                message="文件上传失败"
            )

        if not self._ensure_token():
            return SendResult(
                success=False,
                message="token 无效，无法发送消息"
            )

        target_chat_id = chat_id or self.config.chat_id
        url = f"{FEISHU_API_BASE}{SEND_MESSAGE_API}"

        params = {
            "receive_id_type": "chat_id"
        }

        # 构建文件消息内容
        content = {
            "file_key": file_key
        }

        payload = {
            "receive_id": target_chat_id,
            "msg_type": "file",
            "content": str(content).replace("'", '"')
        }

        try:
            logger.info(f"正在发送文件消息到群组: {target_chat_id}")
            response = requests.post(
                url,
                params=params,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("msg", "未知错误")
                logger.error(f"发送文件消息失败: {error_msg}")
                return SendResult(
                    success=False,
                    message=f"发送失败: {error_msg}",
                    file_key=file_key
                )

            message_id = data.get("data", {}).get("message_id")
            logger.info(f"文件消息发送成功，message_id: {message_id}")

            # 如果有附加文本，发送文本消息
            if text:
                self.send_text_message(text, target_chat_id)

            return SendResult(
                success=True,
                message="发送成功",
                message_id=message_id,
                file_key=file_key
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"发送文件消息请求失败: {e}")
            return SendResult(
                success=False,
                message=f"请求失败: {e}",
                file_key=file_key
            )
        except Exception as e:
            logger.error(f"发送文件消息发生异常: {e}")
            return SendResult(
                success=False,
                message=f"发生异常: {e}",
                file_key=file_key
            )

    def send_excel_report(
        self,
        file_path: Path,
        title: str = "指数估值报告",
        chat_id: Optional[str] = None
    ) -> SendResult:
        """发送 Excel 报告

        Args:
            file_path: Excel 文件路径
            title: 报告标题
            chat_id: 群组 ID，默认使用配置的群组

        Returns:
            SendResult 对象
        """
        if not file_path.exists():
            logger.error(f"Excel 文件不存在: {file_path}")
            return SendResult(
                success=False,
                message=f"文件不存在: {file_path}"
            )

        # 构建消息文本
        date_str = datetime.now().strftime("%Y-%m-%d")
        text = f"【{title}】\n日期: {date_str}\n\n请查收附件中的指数估值报告。"

        logger.info(f"准备发送 Excel 报告: {file_path.name}")
        return self.send_file_message(file_path, text, chat_id)

    def send_post_message(
        self,
        title: str,
        content: list,
        chat_id: Optional[str] = None
    ) -> SendResult:
        """发送富文本消息（卡片消息）

        Args:
            title: 消息标题
            content: 消息内容列表，每个元素为一个段落
            chat_id: 群组 ID，默认使用配置的群组

        Returns:
            SendResult 对象
        """
        if not self._ensure_token():
            return SendResult(
                success=False,
                message="token 无效，无法发送消息"
            )

        target_chat_id = chat_id or self.config.chat_id
        url = f"{FEISHU_API_BASE}{SEND_MESSAGE_API}"

        params = {
            "receive_id_type": "chat_id"
        }

        # 构建富文本内容
        post_content = {
            "zh_cn": {
                "title": title,
                "content": [[{"tag": "text", "text": para}] for para in content]
            }
        }

        import json
        payload = {
            "receive_id": target_chat_id,
            "msg_type": "post",
            "content": json.dumps(post_content, ensure_ascii=False)
        }

        try:
            logger.info(f"正在发送富文本消息到群组: {target_chat_id}")
            response = requests.post(
                url,
                params=params,
                json=payload,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("msg", "未知错误")
                logger.error(f"发送富文本消息失败: {error_msg}")
                return SendResult(
                    success=False,
                    message=f"发送失败: {error_msg}"
                )

            message_id = data.get("data", {}).get("message_id")
            logger.info(f"富文本消息发送成功，message_id: {message_id}")

            return SendResult(
                success=True,
                message="发送成功",
                message_id=message_id
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"发送富文本消息请求失败: {e}")
            return SendResult(
                success=False,
                message=f"请求失败: {e}"
            )
        except Exception as e:
            logger.error(f"发送富文本消息发生异常: {e}")
            return SendResult(
                success=False,
                message=f"发生异常: {e}"
            )


# ============================================================================
# 辅助函数
# ============================================================================

def create_sender_from_env() -> Optional[FeishuSender]:
    """从环境变量创建飞书发送器

    环境变量:
        FEISHU_APP_ID: 飞书应用 ID
        FEISHU_APP_SECRET: 飞书应用密钥
        FEISHU_CHAT_ID: 群组 ID（可选）

    Returns:
        FeishuSender 实例，失败返回 None
    """
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    chat_id = os.environ.get("FEISHU_CHAT_ID", DEFAULT_CHAT_ID)

    if not app_id or not app_secret:
        logger.error("缺少必要的环境变量: FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        return None

    return FeishuSender(app_id, app_secret, chat_id)


# ============================================================================
# 主函数
# ============================================================================

def main():
    """测试函数"""
    import argparse

    parser = argparse.ArgumentParser(description="飞书消息发送器")
    parser.add_argument("--app-id", required=True, help="飞书应用 ID")
    parser.add_argument("--app-secret", required=True, help="飞书应用密钥")
    parser.add_argument("--chat-id", default=DEFAULT_CHAT_ID, help="群组 ID")
    parser.add_argument("--file", help="要发送的文件路径")
    parser.add_argument("--text", help="要发送的文本消息")
    parser.add_argument("--title", default="指数估值报告", help="报告标题")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("飞书消息发送器测试")
    print("=" * 60)

    # 创建发送器
    sender = FeishuSender(args.app_id, args.app_secret, args.chat_id)

    # 获取 token
    if not sender.get_tenant_access_token():
        print("获取 token 失败，请检查 app_id 和 app_secret")
        return

    print("Token 获取成功")

    # 发送文本消息
    if args.text:
        result = sender.send_text_message(args.text)
        print(f"文本消息发送结果: {'成功' if result.success else '失败'} - {result.message}")

    # 发送文件
    if args.file:
        file_path = Path(args.file)
        result = sender.send_excel_report(file_path, args.title)
        print(f"文件发送结果: {'成功' if result.success else '失败'} - {result.message}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()