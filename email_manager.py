#!/usr/bin/env python3
"""
临时邮箱管理器 - 保存和管理邮箱的访问密钥

功能：
1. 创建邮箱时保存 token 到本地
2. 查询已有邮箱的 token
3. 列出所有保存的邮箱
4. 清理过期的邮箱记录
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from curl_cffi import requests


def _load_dotenv(path: str = ".env") -> None:
    """加载 .env 文件"""
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if not key or key in os.environ:
                    continue
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                os.environ[key] = value
    except Exception:
        pass


_load_dotenv()

# ==========================================
# 配置
# ==========================================

EMAIL_STORAGE_FILE = ".email_tokens.json"
TEMP_MAIL_BASE = os.getenv("TEMP_MAIL_BASE", "").rstrip("/")
TEMP_MAIL_ADMIN_PASSWORD = os.getenv("TEMP_MAIL_ADMIN_PASSWORD", "").strip()
TEMP_MAIL_DOMAIN = os.getenv("TEMP_MAIL_DOMAIN", "").strip()
TEMP_MAIL_DOMAINS = [
    d.strip() for d in os.getenv("TEMP_MAIL_DOMAINS", "").split(",") if d.strip()
]


def _ssl_verify() -> bool:
    flag = os.getenv("OPENAI_SSL_VERIFY", "1").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def _temp_mail_admin_headers(*, use_json: bool = False) -> dict:
    if not TEMP_MAIL_ADMIN_PASSWORD:
        raise RuntimeError("未设置 TEMP_MAIL_ADMIN_PASSWORD")
    headers = {"Accept": "application/json", "x-admin-auth": TEMP_MAIL_ADMIN_PASSWORD}
    if TEMP_MAIL_DOMAIN:
        headers["x-custom-auth"] = TEMP_MAIL_DOMAIN
    if use_json:
        headers["Content-Type"] = "application/json"
    return headers


def _temp_mail_domains() -> list:
    """获取临时邮箱域名列表"""
    if TEMP_MAIL_DOMAINS:
        return TEMP_MAIL_DOMAINS
    if TEMP_MAIL_DOMAIN:
        return [TEMP_MAIL_DOMAIN]
    return []


# ==========================================
# 邮箱存储管理
# ==========================================


class EmailStorage:
    """邮箱 token 存储管理"""

    def __init__(self, storage_file: str = EMAIL_STORAGE_FILE):
        self.storage_file = Path(storage_file)
        self.data: Dict[str, dict] = {}
        self._load()

    def _load(self):
        """从文件加载数据"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"[Warning] 加载邮箱存储失败: {e}")
                self.data = {}

    def _save(self):
        """保存数据到文件"""
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Error] 保存邮箱存储失败: {e}")

    def add_email(self, email: str, token: str, metadata: dict = None):
        """添加或更新邮箱"""
        self.data[email] = {
            "token": token,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._save()
        print(f"[✓] 已保存邮箱: {email}")

    def get_email(self, email: str) -> Optional[dict]:
        """获取邮箱信息"""
        if email in self.data:
            # 更新最后使用时间
            self.data[email]["last_used"] = datetime.now().isoformat()
            self._save()
            return self.data[email]
        return None

    def get_token(self, email: str) -> Optional[str]:
        """获取邮箱的 token"""
        info = self.get_email(email)
        return info["token"] if info else None

    def list_emails(self) -> list:
        """列出所有邮箱"""
        emails = []
        for email, info in self.data.items():
            emails.append(
                {
                    "email": email,
                    "created_at": info.get("created_at"),
                    "last_used": info.get("last_used"),
                }
            )
        return sorted(emails, key=lambda x: x["last_used"], reverse=True)

    def delete_email(self, email: str) -> bool:
        """删除邮箱"""
        if email in self.data:
            del self.data[email]
            self._save()
            return True
        return False

    def cleanup_old_emails(self, days: int = 30):
        """清理超过指定天数的邮箱"""
        cutoff = datetime.now() - timedelta(days=days)
        to_delete = []

        for email, info in self.data.items():
            try:
                last_used = datetime.fromisoformat(info.get("last_used", ""))
                if last_used < cutoff:
                    to_delete.append(email)
            except:
                pass

        for email in to_delete:
            self.delete_email(email)

        if to_delete:
            print(f"[✓] 已清理 {len(to_delete)} 个过期邮箱")

        return len(to_delete)


# ==========================================
# 邮箱操作
# ==========================================


def create_email(local: str = None, proxies: dict = None) -> tuple:
    """
    创建临时邮箱并保存 token

    Args:
        local: 邮箱前缀（如 'test123'），如果不指定则随机生成
        proxies: 代理配置

    Returns:
        (email, token) 成功返回邮箱和token，失败返回 ("", "")
    """
    import secrets
    import random

    domains = _temp_mail_domains()
    if not domains:
        print("[Error] 未配置临时邮箱域名")
        return "", ""

    domain = random.choice(domains)

    # 如果没有指定 local，则随机生成
    if not local:
        local = f"oc{secrets.token_hex(5)}"

    print(f"[*] 创建邮箱: {local}@{domain}")

    try:
        create_resp = requests.post(
            f"{TEMP_MAIL_BASE}/admin/new_address",
            headers=_temp_mail_admin_headers(use_json=True),
            json={"enablePrefix": True, "name": local, "domain": domain},
            proxies=proxies,
            impersonate="safari",
            verify=_ssl_verify(),
            timeout=15,
        )

        if create_resp.status_code != 200:
            print(f"[Error] 创建邮箱失败: {create_resp.status_code}")
            print(f"  响应: {create_resp.text[:200]}")
            return "", ""

        data = create_resp.json() if create_resp.content else {}
        email = str(data.get("address") or "").strip()
        token = str(data.get("jwt") or data.get("token") or "").strip()

        if not email or not token:
            print("[Error] 邮箱创建响应缺少必要字段")
            return "", ""

        # 保存到存储
        storage = EmailStorage()
        storage.add_email(
            email,
            token,
            {"domain": domain, "local": local, "created_via": "create_email"},
        )

        print(f"[✓] 邮箱创建成功: {email}")
        print(f"    Token: {token[:50]}...")

        return email, token

    except Exception as e:
        print(f"[Error] 创建邮箱异常: {e}")
        return "", ""


def get_email_token(email: str, proxies: dict = None) -> Optional[str]:
    """
    获取邮箱的 token（优先从本地存储读取）

    Args:
        email: 邮箱地址
        proxies: 代理配置

    Returns:
        token 字符串，如果失败返回 None
    """
    # 先从本地存储读取
    storage = EmailStorage()
    token = storage.get_token(email)

    if token:
        print(f"[✓] 从本地存储读取 token: {email}")
        return token

    # 本地没有，尝试创建同名邮箱
    print(f"[Info] 本地存储中未找到 {email}，尝试创建同名邮箱...")

    if "@" not in email:
        print(f"[Error] 邮箱格式错误: {email}")
        return None

    local, domain = email.split("@", 1)

    try:
        create_resp = requests.post(
            f"{TEMP_MAIL_BASE}/admin/new_address",
            headers=_temp_mail_admin_headers(use_json=True),
            json={"enablePrefix": True, "name": local, "domain": domain},
            proxies=proxies,
            impersonate="safari",
            verify=_ssl_verify(),
            timeout=15,
        )

        if create_resp.status_code == 200:
            data = create_resp.json() if create_resp.content else {}
            new_email = str(data.get("address") or "").strip()
            token = str(data.get("jwt") or data.get("token") or "").strip()

            if new_email == email and token:
                # 保存到存储
                storage.add_email(
                    email,
                    token,
                    {
                        "domain": domain,
                        "local": local,
                        "created_via": "get_email_token",
                    },
                )
                print(f"[✓] 创建同名邮箱成功: {email}")
                return token
            else:
                print(f"[Warning] 创建的邮箱不匹配: {new_email} != {email}")
                return None
        elif create_resp.status_code == 400:
            # 邮箱已存在
            print(f"[Error] 邮箱 {email} 已存在，无法创建")
            print(f"[Info] 请在邮箱服务器上删除该邮箱后重试")
            return None
        else:
            print(f"[Error] 创建邮箱失败: {create_resp.status_code}")
            return None

    except Exception as e:
        print(f"[Error] 获取邮箱 token 异常: {e}")
        return None


def list_saved_emails():
    """列出所有保存的邮箱"""
    storage = EmailStorage()
    emails = storage.list_emails()

    if not emails:
        print("[Info] 本地没有保存的邮箱")
        return

    print(f"\n[*] 已保存的邮箱 ({len(emails)} 个):")
    print("=" * 80)

    for i, info in enumerate(emails, 1):
        print(f"{i}. {info['email']}")
        print(f"   创建时间: {info['created_at']}")
        print(f"   最后使用: {info['last_used']}")
        print()


# ==========================================
# 命令行接口
# ==========================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="临时邮箱管理器")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 创建邮箱
    create_parser = subparsers.add_parser("create", help="创建新邮箱")
    create_parser.add_argument("--local", help="邮箱前缀（如 test123）")

    # 获取 token
    get_parser = subparsers.add_parser("get", help="获取邮箱 token")
    get_parser.add_argument("email", help="邮箱地址")

    # 列出邮箱
    subparsers.add_parser("list", help="列出所有保存的邮箱")

    # 清理
    cleanup_parser = subparsers.add_parser("cleanup", help="清理过期邮箱")
    cleanup_parser.add_argument(
        "--days", type=int, default=30, help="保留天数（默认30天）"
    )

    # 删除邮箱
    delete_parser = subparsers.add_parser("delete", help="删除保存的邮箱")
    delete_parser.add_argument("email", help="邮箱地址")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "create":
        email, token = create_email(local=args.local)
        if email:
            print(f"\n[✓] 邮箱创建成功!")
            print(f"    地址: {email}")
            print(f"    Token: {token}")

    elif args.command == "get":
        token = get_email_token(args.email)
        if token:
            print(f"\n[✓] Token 获取成功!")
            print(f"    邮箱: {args.email}")
            print(f"    Token: {token}")
        else:
            print(f"\n[×] 无法获取邮箱 token")
            return 1

    elif args.command == "list":
        list_saved_emails()

    elif args.command == "cleanup":
        storage = EmailStorage()
        count = storage.cleanup_old_emails(days=args.days)
        print(f"[✓] 已清理 {count} 个过期邮箱")

    elif args.command == "delete":
        storage = EmailStorage()
        if storage.delete_email(args.email):
            print(f"[✓] 已删除邮箱: {args.email}")
        else:
            print(f"[×] 邮箱不存在: {args.email}")
            return 1


if __name__ == "__main__":
    main()
