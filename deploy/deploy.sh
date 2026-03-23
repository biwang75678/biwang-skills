#!/usr/bin/env bash
#
# biwang-skills 部署脚本
# 将 skills/ 下的 skill 同步到 OpenClaw 自定义插件目录
#
# 用法:
#   deploy.sh                          # 部署全部 skill
#   deploy.sh deep-research            # 部署指定 skill
#   deploy.sh deep-research another    # 批量部署指定 skill
#   deploy.sh --dry-run                # 模拟运行(不实际写入)
#   deploy.sh --dry-run deep-research  # 模拟运行指定 skill
#

set -euo pipefail

# ── 路径 ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"

OPENCLAW_PLUGIN_DIR="$HOME/.openclaw/extensions/biwang-skills"
OPENCLAW_SKILLS_DIR="$OPENCLAW_PLUGIN_DIR/skills"

PLUGIN_MANIFEST="$OPENCLAW_PLUGIN_DIR/openclaw.plugin.json"
PLUGIN_ENTRY="$OPENCLAW_PLUGIN_DIR/index.js"
PLUGIN_PACKAGE="$OPENCLAW_PLUGIN_DIR/package.json"

# ── 参数解析 ─────────────────────────────────────────
DRY_RUN=false
SKILLS=()

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=true
            ;;
        -*)
            echo "错误：未知选项 $arg"
            echo "用法：deploy.sh [--dry-run] [skill-name ...]"
            exit 1
            ;;
        *)
            SKILLS+=("$arg")
            ;;
    esac
done

# ── 辅助函数 ─────────────────────────────────────────
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*" >&2; }
error() { echo "[ERROR] $*" >&2; exit 1; }

run_cmd() {
    if $DRY_RUN; then
        echo "[DRY-RUN] $*"
    else
        "$@"
    fi
}

# ── 敏感信息扫描 ─────────────────────────────────────
# 扫描目录中是否含有疑似敏感信息
scan_secrets() {
    local dir="$1"
    local skill_name="$2"
    local patterns=(
        '[Aa][Pp][Ii][-_]?[Kk][Ee][Yy]\s*[:=]'
        '[Ss][Ee][Cc][Rr][Ee][Tt][-_]?[Kk][Ee][Yy]\s*[:=]'
        '[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\s*[:=]'
        '[Tt][Oo][Kk][Ee][Nn]\s*[:=]\s*["\x27][A-Za-z0-9]'
        '[Pp][Rr][Ii][Vv][Aa][Tt][Ee][-_]?[Kk][Ee][Yy]'
        'sk-[A-Za-z0-9]{20,}'
        'ghp_[A-Za-z0-9]{36,}'
        'xoxb-[0-9]'
    )

    local found=false
    for pattern in "${patterns[@]}"; do
        if grep -rEn "$pattern" "$dir" \
            --include='*.md' --include='*.py' --include='*.sh' \
            --include='*.json' --include='*.yaml' --include='*.yml' \
            --include='*.txt' --include='*.toml' --include='*.cfg' \
            --exclude-dir='dev-plans' --exclude-dir='.git' 2>/dev/null; then
            found=true
        fi
    done

    if $found; then
        error "skill [$skill_name] 中发现疑似敏感信息(见上方匹配行)，部署已中止。请先清除敏感信息再重试。"
    fi
}

# ── version 自动递增 ──────────────────────────────────
bump_version() {
    local manifest="$1"
    if [[ ! -f "$manifest" ]]; then
        return
    fi
    # 读取当前 version，patch +1
    local current
    current=$(python3 -c "
import json, sys
with open('$manifest') as f:
    d = json.load(f)
v = d.get('version', '0.0.0')
parts = v.split('.')
parts[-1] = str(int(parts[-1]) + 1)
print('.'.join(parts))
" 2>/dev/null || echo "0.0.1")
    echo "$current"
}

# ── 主逻辑 ───────────────────────────────────────────

# 校验 skills/ 目录
[[ -d "$SKILLS_SRC" ]] || error "skills/ 目录不存在：$SKILLS_SRC"

# 确定部署范围
if [[ ${#SKILLS[@]} -eq 0 ]]; then
    # 全量部署：扫描 skills/ 下所有含 SKILL.md 的子目录
    for d in "$SKILLS_SRC"/*/; do
        name="$(basename "$d")"
        if [[ -f "$d/SKILL.md" ]]; then
            SKILLS+=("$name")
        else
            warn "跳过 $name (缺少 SKILL.md)"
        fi
    done
fi

[[ ${#SKILLS[@]} -gt 0 ]] || error "没有找到可部署的 skill"

info "部署模式：$( $DRY_RUN && echo '模拟运行 (dry-run)' || echo '正式部署' )"
info "部署范围：${SKILLS[*]}"
echo ""

# 逐个 skill 处理
DEPLOYED=()
for skill in "${SKILLS[@]}"; do
    src="$SKILLS_SRC/$skill"

    # 校验 skill 目录
    if [[ ! -d "$src" ]]; then
        warn "skill 目录不存在：$src，跳过"
        continue
    fi
    if [[ ! -f "$src/SKILL.md" ]]; then
        warn "skill [$skill] 缺少 SKILL.md，跳过"
        continue
    fi

    info "── 处理 skill: $skill ──"

    # 敏感信息扫描
    info "扫描敏感信息..."
    scan_secrets "$src" "$skill"
    info "敏感信息扫描通过"

    # 同步到 OpenClaw 自定义插件目录
    info "同步到 OpenClaw: $OPENCLAW_SKILLS_DIR/$skill/"
    run_cmd mkdir -p "$OPENCLAW_SKILLS_DIR/$skill"
    run_cmd rsync -av --delete \
        --exclude='dev-plans/' \
        "$src/" "$OPENCLAW_SKILLS_DIR/$skill/"

    DEPLOYED+=("$skill")
    echo ""
done

# 生成/更新 OpenClaw 插件 manifest
if [[ ${#DEPLOYED[@]} -gt 0 ]]; then
    info "── 更新 OpenClaw 插件配置 ──"

    if $DRY_RUN; then
        if [[ -f "$PLUGIN_MANIFEST" ]]; then
            new_version=$(bump_version "$PLUGIN_MANIFEST")
        else
            new_version="0.1.0"
        fi
        echo "[DRY-RUN] 将创建/更新 $PLUGIN_MANIFEST (version: $new_version)"
        echo "[DRY-RUN] 将创建/更新 $PLUGIN_ENTRY(插件入口)"
        echo "[DRY-RUN] 将创建/更新 $PLUGIN_PACKAGE(package.json)"
    else
        mkdir -p "$OPENCLAW_PLUGIN_DIR"

        if [[ -f "$PLUGIN_MANIFEST" ]]; then
            new_version=$(bump_version "$PLUGIN_MANIFEST")
        else
            new_version="0.1.0"
        fi

        # 生成 openclaw.plugin.json(声明 skills 路径)
        python3 -c "
import json
manifest = {
    'id': 'biwang-skills',
    'name': 'Biwang Custom Skills',
    'version': '$new_version',
    'skills': ['./skills'],
    'configSchema': {'type': 'object', 'additionalProperties': False, 'properties': {}}
}
with open('$PLUGIN_MANIFEST', 'w') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('openclaw.plugin.json 已更新: version $new_version')
"

        # 生成 index.js(最小插件入口，含 register 函数)
        cat > "$PLUGIN_ENTRY" << 'INDEXEOF'
"use strict";
const plugin = {
  id: "biwang-skills",
  name: "Biwang Custom Skills",
  description: "Private custom skills for biwang",
  configSchema: { type: "object", additionalProperties: false, properties: {} },
  register(api) {
    // 纯 skill 插件，无需注册 channel/tool/provider
  }
};
module.exports = plugin;
module.exports.default = plugin;
INDEXEOF
        info "index.js 已生成"

        # 生成 package.json(CommonJS 格式，与 openclaw-lark 一致)
        python3 -c "
import json
pkg = {
    'name': 'biwang-skills',
    'version': '$new_version',
    'main': 'index.js',
    'openclaw': {
        'extensions': ['./index.js']
    }
}
with open('$PLUGIN_PACKAGE', 'w') as f:
    json.dump(pkg, f, indent=2, ensure_ascii=False)
    f.write('\n')
print('package.json 已生成')
"
    fi
    echo ""
fi

# 部署后验证
if [[ ${#DEPLOYED[@]} -gt 0 ]] && ! $DRY_RUN; then
    info "── 部署后验证 ──"
    if command -v openclaw &>/dev/null; then
        echo "运行 openclaw skills check ..."
        openclaw skills check 2>&1 || warn "openclaw skills check 返回非零状态，请人工检查"
    else
        warn "openclaw 命令不可用，跳过验证"
    fi
    echo ""
fi

# 汇总
echo "════════════════════════════════════"
if $DRY_RUN; then
    info "模拟运行完成，未做任何实际变更"
else
    info "部署完成"
fi
info "已部署 skill (${#DEPLOYED[@]})：${DEPLOYED[*]}"
echo "════════════════════════════════════"
