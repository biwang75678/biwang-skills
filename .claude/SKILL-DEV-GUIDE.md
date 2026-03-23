# Skill 开发规范

本文档规范了 biwang-skills 仓库中 Skill 的开发流程，适用于以下两种场景：

1. **开发者**在本仓库内使用 Claude Code、Codex 等 coding agent 开发
2. **用户**在飞书里跟龙虾（OpenClaw）聊天，要求创建或修改某个 skill

## 1) Skill 目录结构

每个 skill 位于 `skills/{skill-name}/` 下，标准结构：

```
skills/{skill-name}/
├── SKILL.md           # Skill 定义入口（必须）
├── dev-plans/         # 开发计划记录（入库）
│   └── YYMMDDHHMMSS-plan.md
├── scripts/           # 脚本/工具（可选）
├── references/        # 参考文档（可选）
└── templates/         # 模板文件（可选）
```

## 2) Plan 前置（强制）

**任何 skill 的创建或修改，必须先创建开发计划文件。**

### Plan 文件规范

- **位置**：`skills/{skill-name}/dev-plans/`
- **文件名**：`YYMMDDHHMMSS-plan.md`（如 `260323143022-plan.md`，精确到秒）
- **新建 skill**：先创建 skill 目录和 `dev-plans/`，再创建 plan 文件

### Plan 文件结构模板

```markdown
# [Skill 名称] - [需求简述]

## 需求描述

[结构化复述用户的原始需求。保留原始意图，清晰化、分层、去冗余。]

## 调研与决策

### 现状分析
[当前 skill 的状态、已有功能]

### 方案对比
[可选方案及优缺点]

### 决策
[选定方案及理由]

## 执行计划

- [ ] 步骤 1：xxx
- [ ] 步骤 2：xxx

## 交互记录

（用户反馈和方案调整按时间顺序记录于此）

## 实施记录

### 变更清单
- [文件路径]: [变更描述]

### 部署
- 提交: [commit hash]
- 部署时间: [时间]
- 部署范围: [全量/指定 skill]
```

## 3) 开发交互流程

```
接到需求
  ↓
在 skills/{skill}/dev-plans/ 创建 YYMMDDHHMMSS-plan.md
  ↓
填写：需求描述 → 调研与决策 → 执行计划
  ↓
判断用户意图 ──→ 用户说"直接干" ──→ 直接进入实施
  │
  └──→ 默认：反馈调研结论和执行计划简要，等待用户确认
          ↓
        用户有新输入 → 更新 plan.md → 反问"是否可以开始实施？"
          ↓
        用户确认 → 进入实施
          ↓
实施修改
  ↓
将进度、结果、变更清单补充到 plan.md 末尾
  ↓
git add + commit + push
  ↓
执行部署：deploy/deploy.sh [skill-names...]
```

## 4) 安全红线

以下规则**绝对不可违反**：

1. **代码和文档中禁止出现敏感信息**：API key、token、密码、私钥、凭证等
2. **plan.md 中禁止记录敏感信息**：如需引用，使用占位符（如 `${API_KEY}`）
3. **提交前自查**：确认 diff 中无敏感信息泄漏
4. **部署脚本会自动扫描**：deploy.sh 在部署前会检测敏感信息模式，发现则中止

## 5) 提交规范

- 提交信息使用中文，简明扼要说明变更内容
- 一个 plan 对应一个或多个 commit（按实际情况拆分）
- push 后应立即执行部署

## 6) 部署

提交并 push 后，使用部署脚本将 skill 同步到运行时环境：

```bash
# 部署全部 skill
deploy/deploy.sh

# 部署指定 skill
deploy/deploy.sh deep-research

# 部署前预览（不实际执行）
deploy/deploy.sh --dry-run
deploy/deploy.sh --dry-run deep-research
```

部署目标：
- **OpenClaw**：`~/.openclaw/extensions/biwang-skills/`（作为独立自定义插件，与飞书插件解耦，所有 agent 自动可用）

deploy.sh 会自动在目标目录生成：
- `openclaw.plugin.json` — 插件 manifest（声明 skills 路径，version 自动递增）
- `index.js` — 最小插件入口（让 OpenClaw 发现此插件）
- `package.json` — 包元数据
- `skills/{skill-name}/` — skill 文件（排除 `dev-plans/`）

部署完成后脚本会自动运行 `openclaw skills check` 验证。如需让龙虾加载新 skill，还需重启 gateway：

```bash
# 正常重启（服务模式）
cd ~ && openclaw gateway restart

# 如果 restart 后仍报 ENOENT，说明有野进程占端口，需先手动杀掉
kill $(lsof -ti:18789); sleep 2; cd ~ && openclaw gateway install --force
```

**注意**：必须先 `cd ~`，避免在临时目录下启动 gateway 导致 ENOENT 崩溃（Claude Code 的 cwd 通常在 `/tmp/` 下）。

## 7) 与 feat-dev/ 的关系

| 维度 | `feat-dev/` | `dev-plans/` |
|------|-------------|--------------|
| 位置 | 仓库根目录 | 每个 skill 目录内 |
| 用途 | 前期调研、技术探索、跨 skill 话题 | 具体 skill 的开发执行闭环 |
| 入库 | 不入库（.gitignore） | 入库 |
| 粒度 | 按日期+序号，全局视角 | 按 skill，skill 视角 |

两者互补：先在 `feat-dev/` 做调研探索，确定方案后在 `dev-plans/` 创建具体执行计划。
