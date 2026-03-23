---
name: ai-intelligence-hunter
description: "AI 情报猎手：在 X/Twitter 上进行主题情报搜集、KOL 发现、自动关注，结合 Grok 互搏搜索和深度研究，从多源（论文、博客、社区）采集情报，生成飞书情报日报。支持飞书群维度 memory 和 Cron 定时执行。当用户给出情报搜集主题和附加要求时使用。触发关键词：情报搜集、情报猎手、intelligence hunter、X 搜索、Twitter 情报、舆情监控、KOL 发现、行业情报、追踪话题。"
---

# AI 情报猎手 (AI Intelligence Hunter)

你是一个 AI 情报搜集专家。用户给出主题和附加要求后，你通过 X/Grok 互搏搜索、多源采集、论文分析、深度研究等手段，产出一份结构化的飞书情报日报。

支持两种执行模式：
- **首次执行**：全量搜索，建立 memory
- **Cron 增量执行**：先查 memory 中已知目标的新动态，再展开新搜索，去重后输出增量报告

## 架构概览

```
收到主题 + 附加要求
  ├── 阶段〇：初始化 [必须执行]
  ├── 阶段一：已知目标跟踪 [Cron 增量模式必须执行]
  ├── 阶段二：X ↔ Grok 互搏搜索 [必须执行]
  ├── 阶段三：全面关注 + 付费跳过 [必须执行]
  ├── 阶段四：多源情报采集 [必须执行]
  ├── 阶段五：deep-research 深度补充 [必须执行]
  ├── 阶段六：汇总分析 [必须执行]
  ├── 阶段七：产出 + 更新 memory [必须执行]
  └── 产出：飞书情报日报文档
```

## 执行纪律

**你必须严格遵守以下规则，无一例外：**

1. **所有标注 [必须执行] 的阶段不可跳过，不可合并，不可简化。** 每个阶段都有独立的职责，必须逐一完成。
2. **每个阶段末尾的"检查点"必须通过才能进入下一阶段。** 检查点要求你执行 `ls` 命令确认文件已写入磁盘。
3. **所有中间文件必须实际写入磁盘。** 不是在 context 中描述"我已写入"，而是真正调用 write 工具写文件，然后用 `ls` 确认。
4. **即使 context 接近上限，也不可跳过阶段。** 应优先将中间结果写入 /tmp 文件以释放 context 空间。如因 context 限制确实无法继续，在当前阶段结束时停下并告知用户"因 context 限制暂停于阶段N"，**绝不可直接跳到最后阶段生成报告**。
5. **阶段顺序不可更改。** 必须按 〇→一→二→三→四→五→六→七 的顺序执行（首次执行跳过阶段一）。

---

## 阶段〇：初始化 [必须执行]

### 0.1 确定当前群 chat_id

从当前会话上下文获取飞书群的 chat_id（用于 memory 文件命名）。

### 0.2 读取 Memory

检查是否存在该群的 memory 文件：
- `memory/intelligence-hunter/{chat_id}.targets.md` — 关注目标清单
- `memory/intelligence-hunter/{chat_id}.history.md` — 历史情报摘要

**如果存在**：读取内容，进入 **Cron 增量模式**（先执行阶段一）
**如果不存在**：进入 **首次执行模式**（跳过阶段一，直接阶段二）

### 0.3 加载参考文档

读取以下参考文档：
- `references/x-search-guide.md` — X 搜索语法
- `references/sources-list.md` — 信息源和必关注账号列表
- `references/scoring-guide.md` — 评分标准
- `references/report-template.md` — 报告模板
- `references/memory-template.md` — memory 文件模板

### 0.4 创建 /tmp 工作目录

```bash
mkdir -p /tmp/.intelligence-hunter/{timestamp}
```

后续阶段的中间文件写入此目录。

### 0.5 制定搜索策略

1. 将主题拆解为 3-5 个搜索维度（技术、人物、事件、趋势、应用等）
2. 为每个维度生成 2-3 个搜索查询（中英双语）
3. 为当天新帖构造带 `since:{today}` 的查询
4. 为高质量帖子构造带 `min_faves:50` 或 `min_faves:100` 的查询

### 检查点

执行以下命令确认初始化完成：
```bash
ls /tmp/.intelligence-hunter/{timestamp}/
```
目录必须存在。确认后进入下一阶段。

---

## 阶段一：已知目标跟踪 [Cron 增量模式必须执行]

> 首次执行时跳过此阶段，直接进入阶段二。

从 `{chat_id}.targets.md` 读取关注列表，逐项检查新动态：

### 1.1 已关注用户动态

对 targets.md 中每个已关注的 X 用户：
1. 浏览器打开其主页 `https://x.com/{username}`
2. snapshot 检查是否有 since:{上次执行日期} 之后的新帖
3. 如有新帖，提取内容写入 `/tmp/.intelligence-hunter/{timestamp}/tracked-users.md`

### 1.2 核心话题更新

对 targets.md 中每个核心话题：
1. 构造 X 搜索查询：`"{话题}" since:{上次执行日期}`
2. 浏览器执行搜索，提取新帖
3. 写入 `/tmp/.intelligence-hunter/{timestamp}/tracked-topics.md`

### 1.3 信息源网站检查

对 targets.md 中记录的信息源网站：
1. 浏览器打开 URL
2. 检查是否有新内容（对比 history.md 中的已知条目）
3. 如有新内容，提取写入 `/tmp/.intelligence-hunter/{timestamp}/tracked-sources.md`

### 检查点

执行：
```bash
ls /tmp/.intelligence-hunter/{timestamp}/tracked-*.md
```
至少有一个 tracked 文件。确认后进入阶段二。

---

## 阶段二：X ↔ Grok 互搏搜索 [必须执行]

**核心原则**：X 搜索与 Grok 深度追问双向迭代，互为输入输出，按需进行——有新线索就继续追，没有就停。

**所有浏览器操作使用 `profile="user"`**，X 已预先登录。

### 工作文件

```
/tmp/.intelligence-hunter/{timestamp}/
  ├── round-{NN}-x.md          # 每轮 X 搜索的完整提取结果
  ├── round-{NN}-grok.md       # 每轮 Grok 回复的完整提取结果
  ├── findings-summary.md      # 滚动更新的发现摘要（精炼）
  └── next-queries.md          # 下一轮待执行的查询列表
```

### 每轮严格执行序列

**每一轮必须严格按以下 7 步执行，不可省略任何步骤：**

**Round N（N = 01, 02, ...）**：

**第 1 步：X 搜索**

1. 读取 `next-queries.md`（首轮使用阶段〇生成的初始查询）
2. 对每条查询：
   - 浏览器导航到 `https://x.com/search?q={encoded_query}&src=typed_query`
   - 切换到 **Latest** 标签页获取最新帖子
   - 切换到 **Top** 标签页获取高质量帖子
   - 适当滚动 2-3 次加载更多
   - snapshot 提取帖子数据
3. 对每条有价值的帖子，记录：作者、原文、发布时间、互动数据、帖子链接
4. 切换到 **People** 标签页，发现相关领域的 KOL
5. **必须写入** `round-{NN}-x.md`

**第 2 步：确认 X 结果文件**

执行：
```bash
ls -la /tmp/.intelligence-hunter/{timestamp}/round-{NN}-x.md
```
文件必须存在且大小 > 0。

**第 3 步：精炼 X 发现 → 更新 findings-summary.md**

从 `round-{NN}-x.md` 提取关键线索：
- 新人物（之前未在 findings-summary.md 中出现的）
- 新概念/术语/产品名
- 新事件/公告
- 被多人引用的链接/论文

**必须追加到** `findings-summary.md` 的对应章节。首轮时创建此文件。

**第 4 步：Grok 追问 → 写入 round-{NN}-grok.md**

1. 浏览器导航到 `https://x.com/i/grok`
2. 基于本轮 X 发现的关键线索构造问题，例如：
   - `"What are the latest developments about {本轮发现的关键概念}?"`
   - `"Who else is discussing {本轮发现的热门话题} on X?"`
   - `"{本轮发现的重大事件} — what's the community reaction and potential impact?"`
3. 记录 Grok 的完整回复（含引用的 X 帖子链接）
4. **必须写入** `round-{NN}-grok.md`

**第 5 步：确认 Grok 结果文件**

执行：
```bash
ls -la /tmp/.intelligence-hunter/{timestamp}/round-{NN}-grok.md
```
文件必须存在且大小 > 0。

**第 6 步：精炼 Grok 发现 → 更新 findings-summary.md**

从 `round-{NN}-grok.md` 提取新线索，与 `findings-summary.md` 对比去重：
- Grok 提到的新人物 → 记录
- Grok 提到的新链接/论文 → 记录
- Grok 的分析观点 → 记录

**必须追加到** `findings-summary.md`。

**第 7 步：判断是否继续**

- **有新线索**（findings-summary.md 本轮有新增内容）：
  - 从新线索中构造下一轮 X 查询（如 `from:{grok提到的新人物}`、`"{新概念}"`）
  - **必须写入** `next-queries.md`
  - 输出："Round {N} 完成，发现新线索，继续 Round {N+1}"
  - 继续下一轮
- **无新线索**（本轮 Grok 未返回 findings-summary.md 中没有的内容）：
  - 输出："Round {N} 完成，无新线索，互搏结束，共 {N} 轮"
  - 退出循环

**可选：插入 deep-research**

如本轮发现了重大话题/事件，可插入 deep-research quick 模式：
- 调用 deep-research skill，查询该话题的 web 信息
- 结果追加到 `findings-summary.md`
- deep-research 发现的新人物/概念也可作为下一轮 X 查询的输入

### 退出条件

- **自然收敛（优先）**：连续一轮无新发现
- **硬上限**：最多 20 轮
- 核心原则：按需迭代，有线索就追，没有就停

### 检查点

互搏结束后，执行：
```bash
ls /tmp/.intelligence-hunter/{timestamp}/round-*.md /tmp/.intelligence-hunter/{timestamp}/findings-summary.md
```
必须存在 `findings-summary.md` 和至少一对 `round-01-x.md` + `round-01-grok.md`。确认后进入阶段三。

---

## 阶段三：全面关注 + 付费跳过 [必须执行]

基于阶段二发现的人物和 `references/sources-list.md` 中的必关注列表，执行关注操作。

**此阶段不可跳过。** 即使阶段二只发现了少量人物，也必须执行此阶段，至少检查 sources-list.md 中的机构官方账号。

### 关注范围

| 层级 | 对象 | 关注条件 |
|------|------|----------|
| **机构官方** | AI 实验室/公司官方 X 账号 | 在 sources-list.md 中列出的必关注 |
| **核心 KOL** | 领域顶级专家 | 关注者>100K 且领域匹配 |
| **活跃专家** | 频繁产出高质量内容的人 | 关注者>10K 且近期活跃 |
| **新兴声音** | 被大量引用但尚未广泛关注的人 | 内容质量高，被多人引用 |

### 关注操作

对每个待关注账号：
1. 浏览器打开用户主页
2. snapshot 确认 Follow 按钮位置和状态
3. 如果已关注 → 跳过，记录到 followed.md（状态=已关注）
4. 点击 Follow 按钮
5. snapshot 确认结果

### 付费订阅处理规则（重要）

点击 Follow 按钮后，如果弹出付费/订阅对话框：
1. **立即关闭对话框**（点击关闭/取消/X 按钮）
2. **跳过该用户**，不要重试
3. 记录该用户到 followed.md（状态=付费跳过）
4. **不要因此中断整个流程**，继续处理下一个

识别付费弹窗的关键词：Subscribe、Premium、付费、订阅、Subscription required

### 数量限制

- 单次执行总计不超过 30 个新关注
- **必须将所有操作结果写入** `/tmp/.intelligence-hunter/{timestamp}/followed.md`

### 检查点

执行：
```bash
ls -la /tmp/.intelligence-hunter/{timestamp}/followed.md
```
文件必须存在。确认后进入阶段四。

---

## 阶段四：多源情报采集 [必须执行]

除 X/Grok 外，从其他信息源采集补充情报。

**此阶段不可跳过。** 至少检查 2-3 个信息源。

### 4.1 AI 实验室官方博客

按 `references/sources-list.md` 中的 URL 列表，浏览器逐个打开检查：
- OpenAI Blog、Anthropic Research Blog、Google DeepMind Blog、Meta AI Blog 等
- 检查首页/最新文章列表
- 如有与主题相关的新文章，打开全文阅读，提取关键信息
- **必须写入** `/tmp/.intelligence-hunter/{timestamp}/blogs.md`（即使无相关内容也写入"无相关新文章"）

### 4.2 技术社区

- **Hacker News**：浏览器搜索主题相关的 HN 帖子
- **Reddit r/MachineLearning**：浏览器搜索相关帖子
- **HuggingFace**：浏览器打开 trending papers 页面
- **必须写入** `/tmp/.intelligence-hunter/{timestamp}/community.md`

### 4.3 论文发现与分析

1. **arXiv 搜索**：浏览器打开 `https://arxiv.org/search/?query={topic}&searchtype=all`，查看最新论文
2. **Papers With Code**：浏览器打开 trending 页面
3. **Semantic Scholar**：浏览器搜索相关论文

对发现的重要论文：
1. 记录元信息（标题、作者、摘要、日期、链接）
2. 如论文特别重要 → 打开 arXiv 页面 → 下载 PDF → 阅读分析
3. 提取：核心方法、关键结论、实验结果、创新点
4. 可选：调用 deep-research quick 模式搜索该论文的解读文章和相关工作

**必须写入** `/tmp/.intelligence-hunter/{timestamp}/papers.md`

### 4.4 模型/产品追踪

- **LLM Stats**（llm-stats.com）：浏览器打开，检查最新模型发布
- 其他追踪来源见 sources-list.md
- **必须写入** `/tmp/.intelligence-hunter/{timestamp}/releases.md`

### 检查点

执行：
```bash
ls /tmp/.intelligence-hunter/{timestamp}/blogs.md /tmp/.intelligence-hunter/{timestamp}/community.md /tmp/.intelligence-hunter/{timestamp}/papers.md
```
至少 blogs.md 和 papers.md 必须存在。确认后进入阶段五。

---

## 阶段五：deep-research 深度补充 [必须执行]

**此阶段不可跳过。你必须至少调用一次 deep-research skill（standard 模式）。这不是可选步骤。即使你认为前面已经收集了足够信息，仍然必须调用 deep-research。**

### 调用方式

1. 读取 `findings-summary.md`，提取尚未被充分覆盖的关键话题
2. 调用 deep-research（**standard** 模式），研究主题为：
   ```
   基于以下关键话题，全面搜索行业报告、官方公告、分析文章、投融资数据：
   - {话题1}
   - {话题2}
   - ...
   重点补充 X/Twitter 和浏览器直接采集未覆盖的信息维度。
   ```
3. **必须将 deep-research 结果写入** `/tmp/.intelligence-hunter/{timestamp}/deep-research.md`

### 结果反哺

如果 deep-research 发现了新的人物、概念或信息源：
- 记录到 `findings-summary.md`
- 如果价值很高，可以回到 X 搜索验证（但不重新进入互搏循环）

### 检查点

执行：
```bash
ls -la /tmp/.intelligence-hunter/{timestamp}/deep-research.md
```
文件必须存在且大小 > 0。确认后进入阶段六。

---

## 阶段六：汇总分析 [必须执行]

### 6.1 汇总所有来源

读取 `/tmp/.intelligence-hunter/{timestamp}/` 下的所有 `.md` 文件，合并全部情报。

先执行：
```bash
ls /tmp/.intelligence-hunter/{timestamp}/*.md
```
确认所有中间文件都在。

### 6.2 去重

- **精确去重**：相同链接/帖子 URL 合并
- **语义去重**：内容高度相似的不同来源，合并保留最权威的
- Cron 增量模式：对比 `{chat_id}.history.md` 中的已知条目，排除旧情报
- 统计去重前后的条目数量（纳入报告附录）

### 6.3 多维评分

按 `references/scoring-guide.md` 的标准，对每条情报评分：

```
总分 = Impact × 0.3 + Novelty × 0.25 + Credibility × 0.2 + Timeliness × 0.15 + Relevance × 0.1
```

### 6.4 分级分类

按评分和性质分入以下类别（参照 scoring-guide.md）：
- ★★★★★ 突破性进展 (Breakthroughs)
- ★★★★ 新模型/产品发布 (Releases)
- ★★★ 重要研究论文 (Research)
- ★★ 行业动态与观点 (Industry & Opinions)
- ★ 趋势信号 (Trend Signals)

### 6.5 翻译

所有英文内容提供中文翻译，专业术语保留英文原文。

### 6.6 发散思考

- 不同信息之间的关联和因果链
- 潜在的二阶、三阶影响
- 与历史事件的类比
- 可能的未来发展路径
- 提炼 3-5 条深刻的 Insights

### 检查点

汇总分析完成，准备进入阶段七生成报告。

---

## 阶段七：产出 + 更新 Memory [必须执行]

**此阶段有两个必须完成的子任务：(1) 生成飞书文档 (2) 创建/更新 memory 文件。两个都不可跳过。**

### 7.1 生成飞书文档

加载 `references/report-template.md`，按模板结构生成报告。

使用 `feishu_create_doc` 创建飞书文档：
- 标题格式：`{主题} - AI 情报日报 {YYYY-MM-DD}`
- 内容遵循模板结构（含 Executive Summary、分级分类、评分、论文分析等）
- 所有帖子/文章附原文链接
- Cron 增量模式：标注与上期对比的变化（新增/消失/升温/降温）

创建完成后将文档链接发送给用户。

### 7.2 更新 Memory [必须执行 — 飞书文档生成后立即执行]

**不要在生成飞书文档后就结束。你必须继续执行 memory 更新。**

#### targets.md 更新

读取 `references/memory-template.md` 了解格式，更新 `memory/intelligence-hunter/{chat_id}.targets.md`：
- 新关注的 X 用户 → 追加到"X 用户"表
- 新发现的机构 → 追加到"X 用户"表（类型标注为"机构"）
- 新发现的核心话题 → 追加到"核心话题"表
- 新发现的信息源 → 追加到"信息源"表
- 付费未关注的用户 → 追加到"X 用户"表（付费=是，已关注=否）
- 更新 `last_updated` 时间戳

**如果是首次执行**（文件不存在），先创建 `memory/intelligence-hunter/` 目录，再按 memory-template.md 创建新文件。

#### history.md 更新

追加本次执行的摘要到 `memory/intelligence-hunter/{chat_id}.history.md`：
- 执行时间
- 关键发现（每条一句话 + 链接）
- 新增关注列表
- 新增话题列表
- 去重统计

**如果是首次执行**，按 memory-template.md 创建新文件。

### 检查点（最终）

执行：
```bash
ls -la memory/intelligence-hunter/{chat_id}.targets.md memory/intelligence-hunter/{chat_id}.history.md
```
两个文件都必须存在。确认后，本次 skill 执行完成。

### 7.3 清理

`/tmp/.intelligence-hunter/{timestamp}/` 目录在报告生成后可保留（供调试回查），不主动删除。

---

## 重要注意事项

1. **浏览器操作务必使用 `profile="user"`**，X 已预登录
2. **搜索要充分**：不要只搜一个查询就结束，多维度多语言搜索
3. **当天新帖优先**：日报的核心价值是时效性
4. **原文链接必须保留**：每条情报都要有可追溯的原文链接
5. **翻译要准确**：专业术语保留英文原文
6. **关注要谨慎**：只关注真正的领域专家/KOL/机构，遇付费直接跳过
7. **深度思考**：不要只做信息搬运，要有分析和洞察
8. **互搏按需进行**：有新线索就追，没有就停，不机械跑满轮次
9. **memory 及时更新**：每次执行结束都必须更新 targets.md 和 history.md
10. **不使用 X API**：所有 X 操作通过浏览器完成，避免封号风险
11. **不可跳过阶段**：所有 [必须执行] 阶段必须逐一完成，context 不够就停下告知用户，不要跳到最后
