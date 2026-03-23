---
name: create-task-group
description: "创建任务群技能：当用户向 bot 布置任务时，自动理解任务、创建飞书任务群、发送结构化任务描述并触发 bot 执行。当用户说'帮我做XX'、'处理XX任务'、'创建任务群'、需要 bot 在独立群中执行较复杂任务时使用。关键词触发：创建任务群、开个群做、帮我处理、执行任务。"
---

# 创建任务群技能 (Create Task Group)

你是一个任务群创建与任务分发的**执行者**。收到用户任务后，自动创建飞书任务群、发送结构化任务描述、并触发目标 bot 开始执行。

## 执行流程

```
收到任务描述
  ├── Step 1: 理解任务 → 精简为 ≤8字 任务名
  ├── Step 2: 获取上下文信息（用户标识、bot 名称）
  ├── Step 3: 创建飞书群（用户为群主，bot 在群内）
  ├── Step 4: 在群内 @用户 发送确认消息 + 结构化任务描述
  ├── Step 5: sessions_send 触发 bot 在群内开始执行
  └── Step 6: 回复用户确认
```

## Step 1: 理解任务并生成任务名

收到用户的任务描述后：

1. **理解任务核心意图**，提取关键动作和对象
2. **精简为 ≤8 个中文字** 的任务名（如"重构登录模块"、"修复支付接口"、"调研向量数据库"）
3. **整理结构化任务描述**，包含：
   - 任务目标（一句话）
   - 具体要求（分点列出）
   - 预期产出
   - 如果需要使用某个 skill，明确标注使用的 skill 名称

## Step 2: 确定当前 agent ID

从对话上下文中获取当前 agent ID。脚本会自动通过 agent ID 查找对应的飞书 bot 凭据和名称。

当前环境的 agent 与 bot 映射（配置于 `~/.openclaw/openclaw.json`）：
- agent `cji1` ↔ 飞书 bot `C记1`
- agent `cji2` ↔ 飞书 bot `C记2`
- agent `cji3` ↔ 飞书 bot `C记3`

## Step 3: 创建飞书群

调用脚本创建群：

```bash
python3 skills/create-task-group/scripts/create_chat.py \
  --name "[任务-{bot名}]{任务名}" \
  --agent-id {当前agentId} \
  --user-id {用户open_id}
```

参数说明：
- `--name`: 群名，格式为 `[任务-{bot名}]{任务名}`
- `--agent-id`: 当前 OpenClaw agent ID（如 `cji1`），脚本自动从 bindings 查找对应飞书凭据
- `--user-id`: 用户 open_id（如 `ou_xxx`），从消息上下文的 SenderId 获取。不传则自动从 sessions.json 发现，发现失败时报错退出
- `--output`: 输出文件路径（默认 `/tmp/.create-task-group/group_info.json`）

脚本自动：
1. 从 `openclaw.json` 的 bindings 查找 agent 对应的飞书 account
2. 从 account 获取 appId/appSecret 和 botName
3. 从 sessions 文件解析用户标识
4. 创建群（用户为群主）

脚本输出 JSON：
```json
{"chat_id": "oc_xxx", "name": "[任务-C记1]重构登录", "agent_id": "cji1", "bot_name": "C记1", "user_id": "用户标识"}
```

**重要**：从输出中提取 `chat_id` 和 `user_id`，后续步骤需要。

## Step 4: 在群内发送确认消息

调用脚本在群内 @用户 发送消息：

```bash
python3 skills/create-task-group/scripts/send_message.py \
  --chat-id {chat_id} \
  --agent-id {当前agentId} \
  --at-user-id {user_id} \
  --text "已收到任务并开始执行！任务描述如下：

【任务目标】
{一句话描述任务目标}

【具体要求】
{分点列出具体要求}

【预期产出】
{预期产出描述}

【使用技能】
{如使用了某个 skill，写明 skill 名称；否则写"无"}"
```

## Step 5: sessions_send 触发 bot 执行

使用 OpenClaw 内置的 `sessions_send` 工具，将结构化任务描述发送到 bot 在新群中的 session，触发 msg turn：

```
工具：sessions_send
参数：
  sessionKey: "agent:{当前agentId}:feishu:group:{chat_id}"
  message: |
    请执行以下任务：

    【任务目标】
    {任务目标}

    【具体要求】
    {具体要求}

    【预期产出】
    {预期产出}

    【使用技能】
    {skill 名称或"无"}

    请开始执行。
  timeoutSeconds: 0
```

**注意**：
- `timeoutSeconds: 0` 表示 fire-and-forget，不等待回复
- sessionKey 中的 `agentId` 使用当前 agent 的 ID
- `chat_id` 来自 Step 3 的输出

## Step 6: 回复用户

在原对话中回复用户：

> 已创建任务群 **{群名}**，任务已开始执行。你可以在群里查看进展。

## 注意事项

1. **任务名长度**：严格控制在 8 个中文字以内，不够凝练时优先保留动词+对象
2. **群名格式**：`[任务-{bot名}]{任务名}`，中括号是群名的一部分
3. **凭据安全**：脚本从 `~/.openclaw/openclaw.json` 读取凭据，不要在日志或消息中输出敏感信息
4. **用户标识**：由脚本自动发现，不要在消息或日志中输出明文标识
5. **错误处理**：如果建群失败，直接告知用户失败原因，不要重试

## Decision Tree

```
收到用户消息
├── 明确说"创建任务群"/"开个群做" → 直接执行本 skill
├── 布置较复杂任务（预计多轮交互） → 建议使用本 skill，确认后执行
├── 简单问答/小任务 → STOP: 直接在当前对话处理，不需要建群
└── 不确定 → 询问用户是否需要创建独立任务群
```
