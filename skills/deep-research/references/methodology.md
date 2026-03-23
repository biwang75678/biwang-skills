# 深度研究方法论：七阶段管线

本文档定义了 deep-research 技能的详细执行方法论。编排 Agent 在对应阶段加载本文件。

## 概览

```
SCOPE → PLAN → SEARCH → ANALYZE → CRITIQUE → SYNTHESIZE → VALIDATE
```

| 模式 | 执行阶段 | 深度 | 广度 | 最少来源 | 目标字数 |
|------|---------|------|------|---------|---------|
| quick | 1,3,6 | 1 | 3 | 5+ | 2000-4000 |
| standard | 1-4,6 | 3 | 4 | 10+ | 4000-8000 |
| deep | 1-7 | 5 | 5 | 15+ | 8000-15000 |

---

## 阶段一：SCOPE（研究定界）

**目标**：明确研究边界、受众和成功标准。

**步骤**：
1. 解析用户研究主题，提取核心概念
2. 确定研究模式（quick/standard/deep），默认 standard
3. 初始化状态：`python3 $CLI init --query "主题" --mode standard`
4. 如果主题模糊，向用户确认范围（仅在必要时）

**默认假设**（减少交互轮次）：
- 技术查询 = 技术受众
- 比较类 = 均衡视角
- 趋势类 = 近 1-2 年

---

## 阶段二：PLAN（策略制定）

> 仅 standard 和 deep 模式执行

**目标**：设计搜索策略，规划查询和 subagent 分配。

**步骤**：

1. **多视角分解**：为研究主题生成 3-5 个研究视角
   - 技术原理视角
   - 应用实践视角
   - 学术/理论视角
   - 商业/市场视角
   - 批判/局限视角

2. **查询规划**：每个视角生成 2-3 个搜索查询
   - 同时使用中文和英文查询
   - 覆盖不同角度：定义、原理、应用、比较、争议、最新进展
   - 查看建议：`python3 $CLI suggest-queries`

3. **搜索角度分解**（8 个维度）：
   - 核心语义（什么是 X）
   - 技术细节（X 如何工作）
   - 最新进展（X 在过去一年的发展）
   - 学术来源（X 的研究论文）
   - 替代观点（X 的竞争对手/替代方案）
   - 统计数据（X 的量化证据）
   - 行业分析（X 的商业应用）
   - 批判分析（X 的局限性/失败模式）

---

## 阶段三：SEARCH（并行搜索）

**目标**：通过 Subagent 递归搜索收集信息。

### 3.1 编排者-Subagent 架构

**核心原则**：原始网页内容永远不进入编排者的上下文窗口。

```
编排 Agent（你）
  ├── 生成查询 + 分组
  ├── 派遣 Subagent A（并行）── WebSearch → WebFetch → 提取 learnings → CLI 写入状态
  ├── 派遣 Subagent B（并行）── 同上
  └── 读取状态文件中的结构化 learnings → 决策
```

### 3.2 每个深度层的执行

**Step 1**：设置当前深度和状态
```bash
python3 $CLI state set-depth "{depth}"
python3 $CLI state set-status "searching"
```

**Step 2**：生成搜索查询（中英双语，多角度）

**Step 3**：将查询分组（每组 2-3 个），为每组派遣一个 subagent

**Step 4**：等待所有 subagent 完成，查看进展
```bash
python3 $CLI state stats
```

### 3.3 Subagent 指令要点

每个 subagent 需要：
- 研究主题和当前深度
- 已有发现概要（最多 30 条，避免重复）
- 分配的搜索查询
- CLI 工具路径

Subagent 的核心工作：
1. 检查查询去重 → `check-query`
2. 执行 WebSearch
3. 逐个 URL：`check-url` → `add-url` → WebFetch
4. **仔细阅读内容，提取高质量 learnings**
5. 生成 follow-up 问题 → `add-followup`

**Learning 质量要求**：
- 包含具体数字、日期、人名、机构名
- 区分事实和观点
- 不要泛泛总结，要有信息增量的具体发现
- 参考已有发现概要，避免重复方向

### 3.4 递归决策

```bash
python3 $CLI state next-depth
```

终止条件（自动判断）：
- 达到最大深度
- 无未使用的 follow-up 问题
- 边际递减（当前层收获 < 上层 20%）

若 `should_continue=true`：
1. 获取 follow-up 问题：`python3 $CLI state followups --limit 5`
2. 标记已用：`python3 $CLI state mark-followup "问题"`
3. 更新深度，基于 follow-up 生成新查询，回到 Step 2

### 3.5 反思暂停（搜索间歇）

在每批 subagent 完成后，暂停评估：
- 找到了哪些关键信息？
- 还缺什么关键方面？
- 信息是否足够回答研究问题？
- 需要继续搜索还是可以进入分析？

---

## 阶段四：ANALYZE（分析整理）

> 仅 standard 和 deep 模式执行

**目标**：对所有 learnings 进行去重、聚类和冲突检测。

```bash
python3 $CLI state set-status "analyzing"
python3 $CLI analyze-learnings
```

分析引擎自动执行：
- **去重**：TF-IDF 余弦相似度 > 0.85 标记为重复
- **聚类**：关键词共现图 → 连通分量 = 主题分组
- **冲突检测**：相似主题 + 否定词模式不对称 → 潜在矛盾

### 大纲动态调整

审查分析结果后，如发现：
- 某个重要主题覆盖不足 → 追加 subagent 补充搜索
- 发现意外的新方向 → 评估是否值得展开
- 某聚类内容过少 → 考虑合并到相关聚类

---

## 阶段五：CRITIQUE（红队审查）

> 仅 deep 模式执行

**目标**：从多个批判视角审查研究发现，识别盲点。

### 三种审查视角

1. **怀疑论从业者**（Skeptical Practitioner）
   - 这些发现在实践中可行吗？
   - 有没有被忽略的实施障碍？

2. **对抗性审稿人**（Adversarial Reviewer）
   - 证据链是否完整？
   - 有没有替代解释？
   - 来源是否存在偏见？

3. **工程可行性视角**（Implementation Engineer）
   - 研究建议是否可操作？
   - 成本和风险是否被充分考虑？

### Critical Gap Loop-Back

如果审查发现**关键知识空白**（不是写作问题，而是信息缺失）：
- 回到阶段三 SEARCH，执行针对性的"补缺查询"
- 限时 3-5 分钟
- 最多回退一次

---

## 阶段六：SYNTHESIZE（综合撰写）

**目标**：生成结构化研究报告。

详见 `references/report-assembly.md`。

---

## 阶段七：VALIDATE（验证交付）

> 仅 deep 模式执行

**目标**：验证报告质量并交付。

```bash
python3 $CLI validate-report research-report.md
```

详见 `references/quality-gates.md`。

---

## 可信度评估

CLI 会自动基于域名评估来源可信度：
- **HIGH**：学术期刊、政府机构、权威媒体、官方文档
- **MEDIUM**：维基百科、技术博客、社区论坛、科技媒体
- **LOW**：自媒体、内容农场、社交媒体

手动检查：`python3 $CLI credibility "https://example.com"`

## 错误处理

- 单个 subagent 失败：记录问题，继续其他 subagent 的结果
- 全部 subagent 失败：检查网络，减少并行数重试
- CLI 命令报错：检查参数格式
- 状态文件损坏：用 `init` 重新初始化
