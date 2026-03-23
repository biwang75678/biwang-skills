# 渐进式报告组装策略

本文档定义了 SYNTHESIZE 阶段的报告生成方法。

## 核心理念

- **逐节生成 + 逐节写入文件**，而非一次性输出整篇报告
- 每节控制在 **≤2000 字**，避免输出 token 限制
- 使用 **sources.json** 持久化引用状态，survive context compaction

## 三种报告格式

| 格式 | 适用场景 | 内容 |
|------|---------|------|
| comprehensive | 全面报告（默认） | 摘要+目录+分节详述+矛盾分析+来源表+方法论 |
| brief | 快速简报 | 主要发现（按可信度排序前15条）+来源列表 |
| outline | 研究大纲 | 分组概要+预览 |

## 组装流程（comprehensive 格式）

### 方式一：一次性生成（默认）

```bash
python3 $CLI state set-status "generating_report"
python3 $CLI generate-report --output research-report.md
```

### 方式二：渐进式逐节生成

适用于长报告（deep 模式、>8000 字），避免 token 溢出：

```bash
# 1. 保存来源索引
python3 $CLI sources

# 2. 逐节生成
python3 $CLI generate-section header
python3 $CLI generate-section summary
python3 $CLI generate-section toc
python3 $CLI generate-section cluster --index 0
python3 $CLI generate-section cluster --index 1
# ... 对每个聚类重复
python3 $CLI generate-section conflicts
python3 $CLI generate-section sources
python3 $CLI generate-section methodology
```

编排 Agent 获取每节的 content 后：
1. 对于 summary 节：替换 `<!-- SUMMARY_PLACEHOLDER -->` 为 200-300 字摘要
2. 对于 cluster 节：在 learning 基础上展开为散文段落
3. 逐节写入（Write/Edit）到 `research-report.md`

### Sources.json 持久化

```bash
python3 $CLI sources
# 输出到当前目录下的 sources.json
```

结构：
```json
[
  {"index": 1, "url": "...", "title": "...", "credibility": "HIGH", "credibility_label": "高可信度"},
  {"index": 2, "url": "...", "title": "...", "credibility": "MEDIUM", "credibility_label": "中等可信度"}
]
```

Context compaction 后可从此文件重新加载引用编号，保持引用连续性。

## 引用规则

- 每条 learning 自带 source_url，报告中使用 `[N]` 格式引用
- 来源按首次出现顺序编号
- 每个重要断言必须即时引用
- 引用编号与来源表一一对应

## 字数目标

| 模式 | 目标字数 | 每节上限 |
|------|---------|---------|
| quick | 2000-4000 | 1000 |
| standard | 4000-8000 | 2000 |
| deep | 8000-15000 | 2000 |

## 报告文件

- 默认保存为 `research-report.md`
- 使用中文撰写，代码/API/术语保留英文
- Markdown 格式，带分级标题、引用、表格
