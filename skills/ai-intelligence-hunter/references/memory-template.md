# Memory 文件模板

本文件定义情报猎手 skill 的群维度 memory 文件格式。

Memory 文件存放于 agent workspace 的 `memory/intelligence-hunter/` 目录下，
以飞书群 chat_id 命名，实现群级隔离。

---

## targets.md 模板

文件路径：`memory/intelligence-hunter/{chat_id}.targets.md`

```markdown
---
name: intelligence-hunter-targets-{群名简称}
description: AI 情报猎手 - {主题} 群的关注目标清单（用户/机构/话题/信息源）
type: reference
last_updated: {YYYY-MM-DD HH:MM}
---

# {主题} 情报群 - 关注目标

## X 用户

| 用户 | 类型 | 领域 | 关注者 | 已关注 | 付费 | 首次发现 | 备注 |
|------|------|------|--------|--------|------|----------|------|

类型：个人 / 机构
已关注：是 / 否
付费：是 / 否 / -（非付费）

## 核心话题

| 话题 | 首次发现 | 最近活跃 | 热度 | 备注 |
|------|----------|----------|------|------|

热度：高 / 上升 / 稳定 / 下降

## 信息源

| 名称 | URL | 类型 | 最后检查 | 备注 |
|------|-----|------|----------|------|

类型：博客 / 论文 / 社区 / 追踪
```

---

## history.md 模板

文件路径：`memory/intelligence-hunter/{chat_id}.history.md`

```markdown
---
name: intelligence-hunter-history-{群名简称}
description: AI 情报猎手 - {主题} 群的历史情报摘要（用于跨次去重）
type: reference
---

# {主题} 情报群 - 历史情报

（每次执行后在文件顶部追加新条目，最新的在最上面）

## {YYYY-MM-DD HH:MM}（第N次执行）

### 关键发现
- [{标题}]({链接}) — {一句话摘要}
- [{标题}]({链接}) — {一句话摘要}

### 新增关注
- @{username}（{领域}，{关注者数}）

### 新增话题
- {话题名}

### 统计
- 互搏轮数：{N}
- 去重前/后：{M} → {N}
- 新关注：{N} 个
- 付费跳过：{N} 个

---

（上一次执行的记录...）
```

---

## 使用说明

### 首次执行

1. 检查 `memory/intelligence-hunter/` 目录是否存在，不存在则创建
2. 按上述模板创建 `{chat_id}.targets.md` 和 `{chat_id}.history.md`
3. 执行完成后填充内容

### Cron 增量执行

1. 读取 `{chat_id}.targets.md`，获取已关注用户/话题/信息源列表
2. 读取 `{chat_id}.history.md`，获取历史情报用于去重
3. 执行完成后：
   - 更新 `targets.md`：追加新发现的用户/话题/信息源
   - 更新 `history.md`：在文件顶部追加本次执行摘要
   - 更新 `targets.md` 的 `last_updated` 时间戳

### 注意事项

- history.md 最新记录在顶部（方便读取时快速对比近期情报）
- 如 history.md 过大（>200 条记录），可清理底部最旧的条目
- targets.md 中"已关注=否 + 付费=是"的用户保留，供用户手动决定
