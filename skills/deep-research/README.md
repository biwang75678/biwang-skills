# Deep Research Skill

对任意主题进行多层递归搜索，生成带引用的中文研究报告。

## 特性

- **七阶段管线**：SCOPE → PLAN → SEARCH → ANALYZE → CRITIQUE → SYNTHESIZE → VALIDATE
- **三种模式**：quick（3 阶段）/ standard（5 阶段）/ deep（7 阶段）
- **编排者-Subagent 分离**：主 agent 上下文保持干净，原始网页内容在 subagent 中处理
- **零外部依赖**：纯 Python stdlib 实现
- **自动分析**：TF-IDF 去重、关键词共现聚类、否定词冲突检测
- **185+ 域名可信度规则**：覆盖中英文学术、政府、媒体、技术社区
- **渐进式报告组装**：逐节生成 + Sources.json 持久化
- **质量门控**：Anti-Truncation、引用验证、占位符检测

## 安装

### Claude Code

```bash
# 方式 1：复制到全局 skills 目录
cp -r skills/deep-research ~/.claude/skills/deep-research

# 方式 2：符号链接
ln -s "$(pwd)/skills/deep-research" ~/.claude/skills/deep-research
```

### Codex CLI

```bash
cp -r skills/deep-research ~/.codex/skills/deep-research
```

安装后，在 Claude Code 中可通过 `/deep-research` 手动调用，或者在对话中说"研究/调研/分析"等关键词自动触发。

## 使用示例

### 场景 1：快速技术调研（quick 模式）

> 用 deep-research 的 quick 模式快速了解一下 WebTransport 协议的现状

效果：
- 1 层搜索，3 个查询
- 访问 5+ 个来源
- 生成 2000-4000 字简报
- 耗时约 2-5 分钟

### 场景 2：标准研究报告（standard 模式，默认）

> 深度研究一下 2026 年大语言模型 Agent 框架的技术对比分析

效果：
- 3 层递归搜索，广度衰减（4 → 3 → 2）
- 访问 10+ 个来源，自动去重和聚类
- 生成 4000-8000 字报告，带引用和矛盾分析
- 耗时约 5-10 分钟

### 场景 3：深度研究（deep 模式）

> 用 deep 模式研究一下合成生物学在碳中和领域的应用前景与挑战

效果：
- 5 层递归搜索，广度衰减（5 → 4 → 3 → 2 → 2）
- 访问 15+ 个来源
- 三角色红队审查（怀疑论从业者/对抗性审稿人/工程师）
- 如发现知识空白，自动回退补充搜索
- 引用验证 + 占位符检测
- 生成 8000-15000 字报告
- 耗时约 10-20 分钟

## 架构说明

```
用户 → 编排 Agent（读 SKILL.md 指令）
              │
              ├── CLI 工具链（Python 脚本）
              │     ├── 状态读写（state_manager）
              │     ├── 内容处理（content_processor）
              │     ├── 分析引擎（learning_analyzer）
              │     └── 报告生成（report_generator）
              │
              └── Subagent（由编排者派遣）
                    ├── WebSearch（搜索）
                    ├── WebFetch（网页抓取）
                    └── CLI 回写状态
```

**关键设计**：编排 Agent 不直接处理原始网页内容，仅通过 JSON 状态文件中的结构化 learnings 进行决策和报告撰写。这是有效的**上下文窗口保护策略**。

## CLI 命令参考

```bash
CLI="skills/deep-research/scripts/cli.py"

# 初始化
python3 $CLI init --query "研究主题" --mode standard

# 状态管理
python3 $CLI state stats                          # 查看研究进度
python3 $CLI state check-query "查询"              # 检查查询是否重复
python3 $CLI state add-learning --text "发现" --url "URL" --title "标题" --depth 0
python3 $CLI state next-depth                      # 递归决策
python3 $CLI state dump                            # 导出完整状态

# 分析
python3 $CLI analyze-learnings                     # 去重/聚类/冲突检测
python3 $CLI suggest-queries                       # 建议查询分配

# 报告
python3 $CLI generate-report --output report.md    # 生成报告
python3 $CLI generate-section cluster --index 0    # 生成单节（渐进式）
python3 $CLI sources                               # 持久化引用索引
python3 $CLI validate-report report.md             # 验证报告质量

# 工具
python3 $CLI credibility "https://example.com"     # 检查域名可信度
```

所有命令输出均为 JSON 格式。

## 文件结构

```
skills/deep-research/
├── SKILL.md                    # 编排指令入口
├── README.md                   # 本文件
├── scripts/
│   ├── cli.py                  # 统一 CLI 入口
│   ├── state_manager.py        # 状态管理（原子写入+文件锁）
│   ├── text_utils.py           # 零依赖 NLP 工具集
│   ├── learning_analyzer.py    # 去重/聚类/冲突检测
│   ├── query_planner.py        # 查询规划+模式配置
│   ├── report_generator.py     # 报告生成+渐进式组装
│   ├── domain_reputation.py    # 域名可信度数据库
│   └── content_processor.py    # HTML/MD 清洗
├── references/
│   ├── methodology.md          # 七阶段详细方法论
│   ├── report-assembly.md      # 渐进式组装策略
│   └── quality-gates.md        # 质量门控标准
└── templates/
    └── report_template.md      # 中文报告模板
```

## 技术细节

- **状态持久化**：JSON 文件 + `fcntl.flock` 文件锁，支持多 subagent 并发写入
- **去重**：URL 规范化 + 查询 BoW 余弦 (0.75) + Learning TF-IDF 余弦 (0.85)
- **聚类**：关键词 overlap coefficient (0.3) + BFS 连通分量
- **冲突检测**：TF-IDF 相似度 (0.5) + 中英文否定词模式不对称
- **广度衰减**：`max(2, int(base_breadth * 0.7^depth))`
- **终止条件**：最大深度 / 无 follow-up / 边际递减 (<20%)

## 许可证

MIT
