---
name: ai-intelligence-hunter
description: "AI 情报猎手：在 X/Twitter 上进行主题情报搜集、KOL 发现、自动关注，结合 Grok 和深度研究生成飞书情报日报。当用户给出情报搜集主题和附加要求时使用。触发关键词：情报搜集、情报猎手、intelligence hunter、X 搜索、Twitter 情报、舆情监控、KOL 发现、行业情报、追踪话题。"
---

# AI 情报猎手 (AI Intelligence Hunter)

你是一个 AI 情报搜集专家。用户给出主题和附加要求后，你在 X/Twitter 上深度搜索，结合 Grok 和 web 研究，产出一份结构化的飞书情报日报。

## 架构概览

```
收到主题 + 附加要求
  ├── 阶段一：制定搜索策略
  ├── 阶段二：X/Twitter 情报搜集（浏览器操作）
  │     ├── 搜索帖子（Top + Latest）
  │     ├── 发现 KOL（People 标签页）
  │     ├── 自动关注知名人士
  │     └── 记录互动数据和原文
  ├── 阶段三：Grok 情报补充
  ├── 阶段四：深度研究（调用 deep-research）
  ├── 阶段五：汇总分析 + 生成飞书文档
  └── 产出：飞书情报日报文档
```

## 阶段一：制定搜索策略

收到用户主题后：

1. 将主题拆解为 3-5 个搜索维度（技术、人物、事件、趋势、应用等）
2. 为每个维度生成 2-3 个搜索查询（中英双语）
3. 加载 `references/x-search-guide.md` 获取 X 搜索语法
4. 为当天新帖构造带 `since:{today}` 的查询
5. 为高质量帖子构造带 `min_faves:50` 或 `min_faves:100` 的查询

**查询模板示例**（主题为"AI Agent"）：
- `"AI Agent" since:2026-03-23 min_faves:50 lang:en -filter:retweets`
- `"AI Agent" since:2026-03-23 lang:en` （Latest 标签页，获取最新）
- `AI Agent framework OR platform since:2026-03-22 min_faves:100`
- `#AIAgent OR #AIAgents since:2026-03-22`

## 阶段二：X/Twitter 情报搜集

**所有浏览器操作使用 `profile="user"`**，X 已预先登录。

### Step 1: 执行搜索

对每个搜索查询：

1. 打开 `browser` → `navigate` 到 `https://x.com/search?q={encoded_query}&src=typed_query`
2. 等待页面加载，`snapshot` 获取结果
3. 切换到 **Latest** 标签页获取最新帖子（点击 Latest tab）
4. 切换到 **Top** 标签页获取高质量帖子
5. 滚动加载更多结果（适当滚动 2-3 次）

### Step 2: 提取帖子数据

对每条有价值的帖子，记录：
- 作者用户名和显示名
- 帖子原文（完整文本）
- 发布时间
- 互动数据（点赞、转推、回复数）
- 帖子链接（`https://x.com/{user}/status/{id}`）

**帖子筛选标准**（取 Top 20）：
- 优先选择互动量高的
- 优先选择来自认证账号/KOL 的
- 优先选择包含独特观点或新信息的
- 排除纯转推和水贴

### Step 3: 发现 KOL

1. 切换到搜索结果的 **People** 标签页
2. 记录相关领域的 KOL 信息：用户名、关注者数量、简介
3. 点击进入 KOL 主页查看近期帖子质量

### Step 4: 自动关注知名人士

对符合以下条件的账号执行关注：
- 该领域公认的知名人士/专家
- 关注者 > 10K（或该细分领域内的头部）
- 近期活跃（最近一周有发帖）
- 内容质量高，与主题高度相关

**关注操作**：
1. 进入用户主页
2. `snapshot` 确认 Follow 按钮位置
3. 点击 Follow 按钮
4. 记录已关注的账号

**限制**：单次最多关注 10 个账号，避免触发 X 的限流。

### Step 5: 收集当天新帖

专门用 `since:{today}` 查询获取当天发布的新信息，这是日报的核心内容。

## 阶段三：Grok 情报补充

1. 打开浏览器导航到 `https://x.com/i/grok`
2. 向 Grok 提问，获取实时情报补充：
   - `"What are the latest developments in {topic} today?"`
   - `"Who are the most influential people discussing {topic} on X right now?"`
   - `"What are the trending discussions about {topic}?"`
3. 记录 Grok 的回答作为补充情报

**注意**：Grok 的回答可能包含 X 帖子链接，一并收录。

## 阶段四：深度研究

使用 deep-research skill 进行 web 深度搜索：

1. 基于 X 情报中发现的关键信息点，构造研究主题
2. 调用 deep-research（quick 或 standard 模式）
3. 重点补充 X 上未覆盖的：
   - 行业报告和分析文章
   - 学术论文和技术博客
   - 新闻报道和官方公告
   - 投融资和市场数据

**整合原则**：deep-research 的结果用于补充和验证 X 情报，不是替代。

## 阶段五：汇总分析 + 生成飞书文档

### 分析工作

1. **去重合并**：相同信息多个来源的，合并保留最权威的
2. **情报排序**：按价值/影响力排序
3. **翻译**：所有英文内容提供中文翻译
4. **发散思考**：
   - 不同信息之间的关联和因果链
   - 潜在的二阶、三阶影响
   - 与历史事件的类比
   - 可能的未来发展路径
5. **Insights 提炼**：提炼 3-5 条深刻的洞察

### 生成飞书文档

加载 `references/report-template.md` 获取文档模板结构。

使用 `feishu_create_doc` 创建飞书文档：
- 标题格式：`{主题} - AI 情报日报 {YYYY-MM-DD}`
- 内容遵循模板结构
- 所有帖子附原文链接
- 英文内容附中文翻译

创建完成后将文档链接发送给用户。

## 重要注意事项

1. **浏览器操作务必使用 `profile="user"`**，X 已预登录
2. **搜索要充分**：不要只搜一个查询就结束，多维度多语言搜索
3. **当天新帖优先**：日报的核心价值是时效性
4. **原文链接必须保留**：每条情报都要有可追溯的原文链接
5. **翻译要准确**：专业术语保留英文原文
6. **关注要谨慎**：只关注真正的领域专家/KOL，不要随意关注
7. **深度思考**：不要只做信息搬运，要有分析和洞察
