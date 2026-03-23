#!/usr/bin/env python3
"""
创建飞书任务群

凭据从 OpenClaw 配置 (~/.openclaw/openclaw.json) 读取，
用户标识从 OpenClaw sessions 文件自动解析。

用法：
    python3 create_chat.py --name "[任务-C记1]重构登录模块" --agent-id cji1
    python3 create_chat.py --name "[任务-C记1]重构登录模块" --agent-id cji1 --output /tmp/group_info.json
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

OPENCLAW_DIR = Path.home() / ".openclaw"
OPENCLAW_CONFIG = OPENCLAW_DIR / "openclaw.json"
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


def load_openclaw_config() -> dict:
    """加载 OpenClaw 配置"""
    if not OPENCLAW_CONFIG.exists():
        print(f"错误：OpenClaw 配置不存在 {OPENCLAW_CONFIG}", file=sys.stderr)
        sys.exit(1)
    return json.loads(OPENCLAW_CONFIG.read_text("utf-8"))


def resolve_account_id(config: dict, agent_id: str) -> str:
    """从 bindings 中找到 agent 对应的飞书 accountId"""
    for binding in config.get("bindings", []):
        if binding.get("agentId") == agent_id:
            match = binding.get("match", {})
            if match.get("channel") == "feishu":
                return match.get("accountId", "")
    print(f"错误：未找到 agent '{agent_id}' 的飞书 binding", file=sys.stderr)
    sys.exit(1)


def load_feishu_creds(config: dict, account_id: str) -> dict:
    """从 OpenClaw 配置中加载飞书凭据"""
    accounts = config.get("channels", {}).get("feishu", {}).get("accounts", {})
    account = accounts.get(account_id, {})
    if not isinstance(account, dict):
        print(f"错误：飞书 account '{account_id}' 配置无效", file=sys.stderr)
        sys.exit(1)

    app_id = account.get("appId", "")
    app_secret = account.get("appSecret", "")
    bot_name = account.get("botName", "")

    if not app_id or not app_secret:
        print(f"错误：飞书 account '{account_id}' 缺少 appId 或 appSecret", file=sys.stderr)
        sys.exit(1)

    return {"app_id": app_id, "app_secret": app_secret, "bot_name": bot_name}


def discover_user_id(agent_id: str) -> str:
    """从 OpenClaw sessions.json 的 key 中解析用户标识"""
    sessions_path = OPENCLAW_DIR / "agents" / agent_id / "sessions" / "sessions.json"
    pattern = re.compile(rf"^agent:{re.escape(agent_id)}:feishu:direct:(.+)$")

    if not sessions_path.exists():
        print(f"警告：sessions 文件不存在 {sessions_path}", file=sys.stderr)
        return ""

    try:
        sessions = json.loads(sessions_path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"警告：读取 sessions.json 失败 ({e})", file=sys.stderr)
        return ""

    for key in sessions:
        m = pattern.match(key)
        if m:
            return m.group(1)

    print(f"警告：未在 sessions.json（{agent_id}）中找到飞书私聊 session", file=sys.stderr)
    return ""


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


def create_group(token: str, group_name: str, user_ids: list = None, owner_id: str = "") -> str:
    """创建群聊，返回 chat_id"""
    body = {"name": group_name, "chat_type": "group"}
    if user_ids:
        body["user_id_list"] = user_ids
    if owner_id:
        body["owner_id"] = owner_id

    result = api_post(
        f"{FEISHU_API_BASE}/im/v1/chats?user_id_type=open_id",
        body,
        headers={"Authorization": f"Bearer {token}"},
    )
    code = result.get("code", -1)
    if code != 0:
        print(f"错误：创建群失败：{json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)

    chat_id = result.get("data", {}).get("chat_id", "")
    if not chat_id:
        print(f"错误：返回结果中无 chat_id：{json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)

    return chat_id


def main() -> None:
    parser = argparse.ArgumentParser(description="创建飞书任务群")
    parser.add_argument("--name", required=True, help="群名称，如 [任务-C记1]重构登录模块")
    parser.add_argument("--agent-id", required=True, help="OpenClaw agent ID（如 cji1）")
    parser.add_argument("--user-id", default="", help="用户 open_id（如 ou_xxx），不传则自动从 sessions.json 发现")
    parser.add_argument("--output", default="/tmp/.create-task-group/group_info.json", help="输出文件路径")
    args = parser.parse_args()

    config = load_openclaw_config()
    account_id = resolve_account_id(config, args.agent_id)
    creds = load_feishu_creds(config, account_id)
    token = get_tenant_token(creds["app_id"], creds["app_secret"])

    user_id = args.user_id or discover_user_id(args.agent_id)
    if not user_id:
        print("错误：无法确定用户 ID，请通过 --user-id 参数指定", file=sys.stderr)
        sys.exit(1)
    user_ids = [user_id]

    chat_id = create_group(token, args.name, user_ids=user_ids or None, owner_id=user_id)

    # 写入群信息
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    info = {
        "chat_id": chat_id,
        "name": args.name,
        "agent_id": args.agent_id,
        "bot_name": creds["bot_name"],
    }
    if user_id:
        info["user_id"] = user_id
    output.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
