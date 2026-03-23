#!/usr/bin/env python3
"""
向飞书群发送富文本消息（支持 @用户）

凭据从 OpenClaw 配置 (~/.openclaw/openclaw.json) 读取。

用法：
    python3 send_message.py --chat-id oc_xxx --agent-id cji1 --at-user-id ou_xxx --text "已收到任务..."
    python3 send_message.py --chat-id oc_xxx --agent-id cji1 --text "纯文本消息"
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


def load_feishu_creds(agent_id: str) -> dict:
    """从 OpenClaw 配置加载飞书凭据"""
    if not OPENCLAW_CONFIG.exists():
        print(f"错误：OpenClaw 配置不存在 {OPENCLAW_CONFIG}", file=sys.stderr)
        sys.exit(1)

    config = json.loads(OPENCLAW_CONFIG.read_text("utf-8"))

    # 从 bindings 找 agent 对应的 accountId
    account_id = ""
    for binding in config.get("bindings", []):
        if binding.get("agentId") == agent_id:
            match = binding.get("match", {})
            if match.get("channel") == "feishu":
                account_id = match.get("accountId", "")
                break
    if not account_id:
        print(f"错误：未找到 agent '{agent_id}' 的飞书 binding", file=sys.stderr)
        sys.exit(1)

    account = config.get("channels", {}).get("feishu", {}).get("accounts", {}).get(account_id, {})
    app_id = account.get("appId", "")
    app_secret = account.get("appSecret", "")
    if not app_id or not app_secret:
        print(f"错误：飞书 account '{account_id}' 缺少 appId 或 appSecret", file=sys.stderr)
        sys.exit(1)

    return {"app_id": app_id, "app_secret": app_secret}


def api_post(url: str, data: dict, headers: dict = None) -> dict:
    """POST 请求到飞书 API"""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"错误：飞书 API 返回 {e.code}：{body}", file=sys.stderr)
        sys.exit(1)


def get_tenant_token(app_id: str, app_secret: str) -> str:
    """获取 tenant_access_token"""
    result = api_post(
        f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal",
        {"app_id": app_id, "app_secret": app_secret},
    )
    token = result.get("tenant_access_token", "")
    if not token:
        print(f"错误：获取 tenant_access_token 失败：{json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)
    return token


def send_post_message(token: str, chat_id: str, text: str, at_user_id: str = "") -> dict:
    """发送富文本消息到群，支持 @用户"""
    content_elements = []
    if at_user_id:
        content_elements.append({"tag": "at", "user_id": at_user_id})
        content_elements.append({"tag": "text", "text": " "})

    content_elements.append({"tag": "text", "text": text})

    post_content = json.dumps({
        "zh_cn": {
            "content": [content_elements],
        }
    }, ensure_ascii=False)

    body = {
        "receive_id": chat_id,
        "msg_type": "post",
        "content": post_content,
    }

    result = api_post(
        f"{FEISHU_API_BASE}/im/v1/messages?receive_id_type=chat_id",
        body,
        headers={"Authorization": f"Bearer {token}"},
    )
    code = result.get("code", -1)
    if code != 0:
        print(f"错误：发送消息失败：{json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)

    message_id = result.get("data", {}).get("message_id", "")
    print(json.dumps({"message_id": message_id, "chat_id": chat_id}, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="向飞书群发送富文本消息")
    parser.add_argument("--chat-id", required=True, help="群 chat_id")
    parser.add_argument("--agent-id", required=True, help="OpenClaw agent ID（如 cji1）")
    parser.add_argument("--text", required=True, help="消息文本内容")
    parser.add_argument("--at-user-id", default="", help="需要 @的用户标识")
    args = parser.parse_args()

    creds = load_feishu_creds(args.agent_id)
    token = get_tenant_token(creds["app_id"], creds["app_secret"])
    send_post_message(token, args.chat_id, args.text, at_user_id=args.at_user_id)


if __name__ == "__main__":
    main()
