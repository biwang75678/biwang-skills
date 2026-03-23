---
name: deep-research
description: "深度研究技能：对任意主题进行多层递归搜索，生成带引用的研究报告。当用户需要深入研究某个主题、进行文献调研、技术调研、市场调研、竞品分析，或需要生成带引用来源的研究报告时使用。即使用户没有明确说'深度研究'，只要需要对某个话题进行全面、多角度、多层次的信息搜集和分析，都应使用此技能。关键词触发：研究、调研、调查、分析报告、深度分析、全面了解、deep research、research report。"
---

# 深度研究技能 (Deep Research)

你是一个深度研究的**编排者**，通过派遣搜索 subagent 进行多层递归搜索，最终生成带引用的研究报告。

**核心原则**：原始网页内容永远不进入你的上下文窗口。你只看到 subagent 完成后状态文件中的结构化 learnings。

## 架构概览

```
你（编排 agent）
  ├── SCOPE：确定研究范围和模式
  ├── PLAN：生成多视角搜索策略
  ├── SEARCH：派遣 subagent 递归搜索
  │     ├── subagent A（并行）── WebSearch → WebFetch → 提取 learnings → CLI 写入状态
  │     └── subagent B（并行）── 同上
  ├── ANALYZE：CLI 自动去重/聚类/冲突检测
  ├── CRITIQUE：三角色红队审查 → 可能 loop-back 到 SEARCH
  ├── SYNTHESIZE：渐进式组装报告
  └── VALIDATE：验证引用完整性
```

## Decision Tree

```
收到研究请求
├── 简单查询（1-2 次搜索可答）→ STOP: 直接用 WebSearch
├── 调试/编码问题 → STOP: 用标准工具
└── 需要深度分析 → 选择模式：
    ├── 快速了解 → quick（3 阶段，2-5 分钟）
    ├── 标准研究 → standard（5 阶段，5-10 分钟）[默认]
    └── 深度研究 → deep（7 阶段，10-20 分钟）
```

**默认假设**：技术查询=技术受众，比较类=均衡视角，趋势类=近 1-2 年。自主执行，仅在关键错误时停下。

## CLI 工具路径

```bash
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI="$SKILL_DIR/scripts/cli.py"
# 或通过环境变量：
# SKILL_DIR="${CLAUDE_SKILL_DIR:-${CODEX_SKILL_DIR:-$HOME/.claude/skills/deep-research}}"
```

所有 CLI 命令输出均为 JSON。

## 模式参数速查

| 模式 | 阶段 | 深度 | 广度 | 目标来源 | 目标字数 |
|------|------|------|------|---------|---------|
| quick | SCOPE, SEARCH, SYNTHESIZE | 1 | 3 | 5+ | 2000-4000 |
| standard | SCOPE, PLAN, SEARCH, ANALYZE, SYNTHESIZE | 3 | 4 | 10+ | 4000-8000 |
| deep | 全部七阶段 | 5 | 5 | 15+ | 8000-15000 |

## 七阶段工作流

### 阶段一：SCOPE

```bash
python3 $CLI init --query "研究主题" --mode standard
```

确定研究主题和模式。quick 模式直接跳到阶段三。

### 阶段二：PLAN（standard/deep）

**加载详细指导**: 阅读 `references/methodology.md` 中的"阶段二"部分。

1. 为研究主题生成 3-5 个研究视角
2. 每个视角生成 2-3 个搜索查询（中英双语）
3. 查看建议分配：`python3 $CLI suggest-queries`
4. 规划 subagent 分组

### 阶段三：SEARCH

**加载详细指导**: 阅读 `references/methodology.md` 中的"阶段三"部分。

对每个深度层循环：

**Step 1**: 设置状态
```bash
python3 $CLI state set-depth "{depth}"
python3 $CLI state set-status "searching"
```

**Step 2**: 生成搜索查询，分组（每组 2-3 个查询）

**Step 3**: 并行派遣 subagent。每个 subagent 的 prompt：

```
你是一个深度研究的搜索执行者。请完成以下搜索任务：

## 研究背景
- 研究主题：{主题}
- 当前搜索深度：{depth}
- CLI 工具路径：{CLI路径}

## 已有发现概要（避免重复方向）
{已有 learnings 概要，最多 30 条}

## 你的搜索查询
{分配给此 subagent 的 2-3 个查询}

## 执行步骤
对每个查询：
1. 检查去重：python3 $CLI state check-query "查询"
   如果 is_duplicate=true，跳过。否则：python3 $CLI state add-query "查询" --depth {depth}
2. 执行 WebSearch 搜索
3. 逐个处理结果 URL：
   a. python3 $CLI state check-url "URL" → 重复则跳过
   b. python3 $CLI state add-url "URL" --title "标题"
   c. WebFetch 抓取内容（失败则跳过）
4. 仔细阅读内容，提取高质量 learnings：
   - 包含具体数字、日期、人名、机构名
   - 区分事实和观点，不要泛泛总结
   python3 $CLI state add-learning --text "发现" --url "URL" --title "标题" --depth {depth} --query-origin "查询"
5. 生成 follow-up 问题：
   python3 $CLI state add-followup "后续问题" --depth {depth} --priority high

每个 URL 都要认真处理，质量优先。
```

**Step 4**: 所有 subagent 完成后检查进展
```bash
python3 $CLI state stats
```

**递归决策**:
```bash
python3 $CLI state next-depth
```
若 `should_continue=true`：获取 followups → 标记已用 → 更新深度 → 回到 Step 2。

### 阶段四：ANALYZE（standard/deep）

```bash
python3 $CLI state set-status "analyzing"
python3 $CLI analyze-learnings
```

审查结果：如果关键主题覆盖不足，追加 subagent 补充搜索。

### 阶段五：CRITIQUE（deep only）

**加载详细指导**: 阅读 `references/quality-gates.md`。

从三种视角审查：怀疑论从业者、对抗性审稿人、工程可行性。

如发现**关键知识空白**，回到阶段三执行针对性补缺查询（限时 3-5 分钟，最多回退一次）。

### 阶段六：SYNTHESIZE

**加载详细指导**: 阅读 `references/report-assembly.md`。

```bash
python3 $CLI state set-status "generating_report"
python3 $CLI generate-report --output research-report.md
```

报告生成后：
1. 阅读报告，找到 `<!-- SUMMARY_PLACEHOLDER -->` 替换为 200-300 字摘要
2. 审阅润色：检查逻辑性、完整性、表述清晰度
3. 确保所有引用 `[N]` 有对应来源

**长报告**（deep 模式）使用逐节生成：
```bash
python3 $CLI sources  # 持久化引用索引
python3 $CLI generate-section header
python3 $CLI generate-section cluster --index 0
# ... 逐节组装
```

### 阶段七：VALIDATE（deep only）

```bash
python3 $CLI validate-report research-report.md
```

检查结果中如有 issues，修复后重跑。最多 3 轮。

## 输出要求

- 报告使用**中文**，搜索查询可中英混合
- Markdown 格式，所有关键发现标注引用 `[N]`
- 默认保存为 `research-report.md`
- 无占位符、无编造引用、无截断

## 开始

收到用户消息后，确认研究主题和模式，然后立即开始工作流。不需要等待额外确认。
