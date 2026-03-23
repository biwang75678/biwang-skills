"""
Report generator: Chinese Markdown report with citations and progressive assembly.
"""

import json
import os
import re
from datetime import datetime, timezone

try:
    from . import domain_reputation
except ImportError:
    import domain_reputation  # type: ignore[no-redef]


def _build_source_list(learnings: list[dict]) -> list[dict]:
    """Build deduplicated source list with credibility ratings."""
    seen_urls = set()
    sources = []
    idx = 1
    for l in learnings:
        if l.get("is_duplicate"):
            continue
        url = l.get("source_url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        cred = l.get("credibility", domain_reputation.MEDIUM)
        sources.append({
            "index": idx,
            "url": url,
            "title": l.get("source_title", url),
            "credibility": cred,
            "credibility_label": domain_reputation.get_credibility_label(cred),
        })
        idx += 1
    return sources


def _url_to_index(sources: list[dict]) -> dict[str, int]:
    """Map URL to citation index."""
    return {s["url"]: s["index"] for s in sources}


def _group_by_cluster(learnings, analysis):
    """Group active learnings by cluster."""
    active = [l for l in learnings if not l.get("is_duplicate")]

    if not analysis or not analysis.get("clusters"):
        # No clustering data — single group
        return [{"label": "研究发现", "keywords": [], "learnings": active}]

    clusters = analysis["clusters"]
    cluster_map: dict[int, dict] = {}
    for c in clusters:
        cluster_map[c["cluster_id"]] = {
            "label": c.get("label", f"主题 {c['cluster_id']}"),
            "keywords": c.get("keywords", []),
            "learnings": [],
        }

    unclustered = []
    for l in active:
        cid = l.get("cluster_id")
        if cid is not None and cid in cluster_map:
            cluster_map[cid]["learnings"].append(l)
        else:
            unclustered.append(l)

    groups = [v for v in cluster_map.values() if v["learnings"]]
    if unclustered:
        groups.append({"label": "其他发现", "keywords": [], "learnings": unclustered})

    return groups


def generate_comprehensive(state: dict) -> str:
    """Generate comprehensive Chinese research report."""
    config = state["config"]
    learnings = state["learnings"]
    analysis = state.get("analysis")
    urls_visited = state["urls_visited"]
    queries_executed = state["queries_executed"]

    sources = _build_source_list(learnings)
    url_idx = _url_to_index(sources)

    groups = _group_by_cluster(learnings, analysis)

    active_count = len([l for l in learnings if not l.get("is_duplicate")])

    lines = []

    # Title
    lines.append(f"# 深度研究报告：{config['query']}\n")

    # Metadata
    lines.append(f"> 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"> 搜索深度：{config['max_depth']} 层 | 访问来源：{len(urls_visited)} 个 | "
                 f"有效发现：{active_count} 条 | 搜索查询：{len(queries_executed)} 次\n")

    # Summary placeholder
    lines.append("## 摘要\n")
    lines.append("<!-- SUMMARY_PLACEHOLDER: Agent 应在此撰写 200-300 字的研究摘要 -->")
    lines.append('<!-- ANTI-TRUNCATION: 本报告每一节都必须完整生成，禁止使用"内容省略""待补充""此处略"等占位符 -->\n')

    # Table of contents
    lines.append("## 目录\n")
    for i, group in enumerate(groups, 1):
        lines.append(f"{i}. [{group['label']}](#{i}-{group['label'].replace(' ', '-')})")
    lines.append(f"{len(groups) + 1}. [矛盾与争议](#矛盾与争议)")
    lines.append(f"{len(groups) + 2}. [信息来源](#信息来源)")
    lines.append(f"{len(groups) + 3}. [研究方法说明](#研究方法说明)")
    lines.append("")

    # Main sections by cluster
    for i, group in enumerate(groups, 1):
        lines.append(f"## {i}. {group['label']}\n")
        if group["keywords"]:
            lines.append(f"**关键词**: {', '.join(group['keywords'][:5])}\n")

        for l in group["learnings"]:
            text = l["text"]
            url = l.get("source_url", "")
            cite = ""
            if url and url in url_idx:
                cite = f" [{url_idx[url]}]"
            lines.append(f"- {text}{cite}")
        lines.append("")

    # Conflicts section
    lines.append("## 矛盾与争议\n")
    conflicts = analysis.get("conflicts", []) if analysis else []
    if conflicts:
        for c in conflicts:
            lines.append(f"### 矛盾发现\n")
            a_cite = ""
            b_cite = ""
            # Find URLs for conflict learnings
            for l in learnings:
                if l["id"] == c.get("learning_a") and l.get("source_url") in url_idx:
                    a_cite = f" [{url_idx[l['source_url']]}]"
                if l["id"] == c.get("learning_b") and l.get("source_url") in url_idx:
                    b_cite = f" [{url_idx[l['source_url']]}]"
            lines.append(f"- **观点 A**{a_cite}: {c.get('text_a', '')}")
            lines.append(f"- **观点 B**{b_cite}: {c.get('text_b', '')}")
            lines.append(f"- 相似度: {c.get('similarity', 'N/A')}")
            lines.append("")
    else:
        lines.append("本次研究未发现明显矛盾信息。\n")

    # Sources section
    lines.append("## 信息来源\n")
    lines.append("| 编号 | 来源 | 可信度 |")
    lines.append("|------|------|--------|")
    for s in sources:
        title = s["title"][:60] + ("..." if len(s["title"]) > 60 else "")
        lines.append(f"| [{s['index']}] | [{title}]({s['url']}) | {s['credibility_label']} |")
    lines.append("")

    # Methodology section
    lines.append("## 研究方法说明\n")
    lines.append("本报告由深度研究代理自动生成，采用以下方法：\n")
    lines.append(f"1. **递归搜索**: 最大深度 {config['max_depth']} 层，基础广度 {config['base_breadth']}")
    lines.append(f"2. **来源数量**: 访问了 {len(urls_visited)} 个不同来源")
    lines.append(f"3. **查询数量**: 执行了 {len(queries_executed)} 次搜索查询")
    lines.append(f"4. **去重处理**: 对重复发现进行了自动去重")
    lines.append(f"5. **主题聚类**: 使用关键词共现分析对发现进行了分组")
    lines.append(f"6. **冲突检测**: 自动检测了信息间的潜在矛盾")
    lines.append(f"7. **来源评估**: 基于域名可信度数据库对来源进行了评级")
    lines.append("")

    return "\n".join(lines)


def generate_brief(state: dict) -> str:
    """Generate brief summary report."""
    config = state["config"]
    learnings = state["learnings"]
    analysis = state.get("analysis")
    urls_visited = state["urls_visited"]

    sources = _build_source_list(learnings)
    url_idx = _url_to_index(sources)

    active = [l for l in learnings if not l.get("is_duplicate")]

    lines = []
    lines.append(f"# 研究简报：{config['query']}\n")
    lines.append(f"> 访问 {len(urls_visited)} 个来源 | {len(active)} 条有效发现\n")

    lines.append("## 主要发现\n")
    # Show up to 15 most important learnings (HIGH credibility first)
    cred_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_active = sorted(active, key=lambda l: cred_order.get(l.get("credibility", "MEDIUM"), 1))
    for l in sorted_active[:15]:
        url = l.get("source_url", "")
        cite = f" [{url_idx[url]}]" if url in url_idx else ""
        lines.append(f"- {l['text']}{cite}")
    lines.append("")

    lines.append("## 来源\n")
    for s in sources:
        lines.append(f"[{s['index']}] [{s['title']}]({s['url']}) ({s['credibility_label']})")
    lines.append("")

    return "\n".join(lines)


def generate_outline(state: dict) -> str:
    """Generate outline report."""
    config = state["config"]
    learnings = state["learnings"]
    analysis = state.get("analysis")

    groups = _group_by_cluster(learnings, analysis)

    lines = []
    lines.append(f"# 研究大纲：{config['query']}\n")

    for i, group in enumerate(groups, 1):
        lines.append(f"## {i}. {group['label']}")
        if group["keywords"]:
            lines.append(f"   关键词: {', '.join(group['keywords'][:5])}")
        lines.append(f"   发现数: {len(group['learnings'])}")
        # Show first 3 learnings as preview
        for l in group["learnings"][:3]:
            lines.append(f"   - {l['text'][:80]}...")
        lines.append("")

    return "\n".join(lines)


def generate_report(state: dict, report_type: str = "") -> str:
    """Generate report based on type."""
    rtype = report_type or state["config"].get("report_type", "comprehensive")
    if rtype == "brief":
        return generate_brief(state)
    elif rtype == "outline":
        return generate_outline(state)
    else:
        return generate_comprehensive(state)


def save_sources_json(state: dict, output_dir: str = ".") -> dict:
    """Persist sources list to standalone sources.json for progressive assembly."""
    sources = _build_source_list(state["learnings"])
    path = os.path.join(output_dir, "sources.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    return {"status": "ok", "path": path, "total_sources": len(sources)}


def generate_section(state: dict, section_type: str, section_index: int = 0) -> str:
    """Generate a single report section for progressive assembly.

    section_type: "header" | "summary" | "toc" | "cluster" | "conflicts" | "sources" | "methodology"
    section_index: cluster index (for section_type="cluster")
    """
    config = state["config"]
    learnings = state["learnings"]
    analysis = state.get("analysis")
    sources = _build_source_list(learnings)
    url_idx = _url_to_index(sources)
    groups = _group_by_cluster(learnings, analysis)
    active_count = len([l for l in learnings if not l.get("is_duplicate")])

    if section_type == "header":
        lines = [f"# 深度研究报告：{config['query']}\n"]
        lines.append(f"> 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"> 搜索深度：{config['max_depth']} 层 | 访问来源：{len(state['urls_visited'])} 个 | "
                     f"有效发现：{active_count} 条 | 搜索查询：{len(state['queries_executed'])} 次\n")
        return "\n".join(lines)

    elif section_type == "summary":
        return ("## 摘要\n\n"
                "<!-- SUMMARY_PLACEHOLDER: Agent 应在此撰写 200-300 字的研究摘要 -->\n"
                "<!-- ANTI-TRUNCATION: 本节必须完整生成 -->\n")

    elif section_type == "toc":
        lines = ["## 目录\n"]
        for i, group in enumerate(groups, 1):
            lines.append(f"{i}. [{group['label']}](#{i}-{group['label'].replace(' ', '-')})")
        lines.append(f"{len(groups) + 1}. [矛盾与争议](#矛盾与争议)")
        lines.append(f"{len(groups) + 2}. [信息来源](#信息来源)")
        lines.append(f"{len(groups) + 3}. [研究方法说明](#研究方法说明)\n")
        return "\n".join(lines)

    elif section_type == "cluster":
        if section_index >= len(groups):
            return ""
        group = groups[section_index]
        lines = [f"## {section_index + 1}. {group['label']}\n"]
        lines.append("<!-- ANTI-TRUNCATION: 本节必须完整生成，禁止省略 -->\n")
        if group["keywords"]:
            lines.append(f"**关键词**: {', '.join(group['keywords'][:5])}\n")
        for l in group["learnings"]:
            url = l.get("source_url", "")
            cite = f" [{url_idx[url]}]" if url in url_idx else ""
            lines.append(f"- {l['text']}{cite}")
        lines.append("")
        return "\n".join(lines)

    elif section_type == "conflicts":
        lines = ["## 矛盾与争议\n"]
        conflicts = analysis.get("conflicts", []) if analysis else []
        if conflicts:
            for c in conflicts:
                lines.append("### 矛盾发现\n")
                lines.append(f"- **观点 A**: {c.get('text_a', '')[:200]}")
                lines.append(f"- **观点 B**: {c.get('text_b', '')[:200]}")
                lines.append(f"- 相似度: {c.get('similarity', 'N/A')}\n")
        else:
            lines.append("本次研究未发现明显矛盾信息。\n")
        return "\n".join(lines)

    elif section_type == "sources":
        lines = ["## 信息来源\n"]
        lines.append("| 编号 | 来源 | 可信度 |")
        lines.append("|------|------|--------|")
        for s in sources:
            title = s["title"][:60] + ("..." if len(s["title"]) > 60 else "")
            lines.append(f"| [{s['index']}] | [{title}]({s['url']}) | {s['credibility_label']} |")
        lines.append("")
        return "\n".join(lines)

    elif section_type == "methodology":
        lines = ["## 研究方法说明\n"]
        lines.append("本报告由深度研究代理自动生成，采用以下方法：\n")
        lines.append(f"1. **递归搜索**: 最大深度 {config['max_depth']} 层，基础广度 {config['base_breadth']}")
        lines.append(f"2. **来源数量**: 访问了 {len(state['urls_visited'])} 个不同来源")
        lines.append(f"3. **查询数量**: 执行了 {len(state['queries_executed'])} 次搜索查询")
        lines.append("4. **去重处理**: 对重复发现进行了自动去重")
        lines.append("5. **主题聚类**: 使用关键词共现分析对发现进行了分组")
        lines.append("6. **冲突检测**: 自动检测了信息间的潜在矛盾")
        lines.append("7. **来源评估**: 基于域名可信度数据库对来源进行了评级\n")
        return "\n".join(lines)

    return ""


def validate_report(report_content: str, state: dict) -> dict:
    """Validate report citations and quality."""
    issues = []
    warnings = []

    # 1. Extract citation indices from report
    citation_pattern = re.compile(r"\[(\d+)\]")
    cited_indices = set()
    for m in citation_pattern.finditer(report_content):
        cited_indices.add(int(m.group(1)))

    # 2. Build source list and check citation integrity
    sources = _build_source_list(state["learnings"])
    available_indices = {s["index"] for s in sources}
    missing = cited_indices - available_indices
    unused = available_indices - cited_indices

    if missing:
        issues.append(f"引用了不存在的来源编号: {sorted(missing)}")

    # 3. Cross-check URLs in report against visited
    url_pattern = re.compile(r"https?://[^\s\)]+")
    report_urls = set(url_pattern.findall(report_content))
    visited_urls = {u["url"] for u in state["urls_visited"]}
    unvisited_urls = report_urls - visited_urls
    if unvisited_urls:
        issues.append(f"报告中包含 {len(unvisited_urls)} 个未在研究中访问的 URL")

    # 4. Detect placeholders and truncation
    placeholder_patterns = [
        r"TODO", r"TBD", r"PLACEHOLDER", r"FIXME",
        r"内容省略", r"此处略", r"待补充", r"待完善",
        r"Content continues", r"Due to length", r"此处省略",
    ]
    placeholders_found = []
    for pat in placeholder_patterns:
        matches = re.findall(pat, report_content, re.IGNORECASE)
        placeholders_found.extend(matches)
    if placeholders_found:
        issues.append(f"发现 {len(placeholders_found)} 个占位符/截断文本: {placeholders_found[:5]}")

    # 5. Check citation range shortcuts (e.g., [3-50])
    range_pattern = re.compile(r"\[(\d+)-(\d+)\]")
    ranges = range_pattern.findall(report_content)
    if ranges:
        issues.append(f"发现 {len(ranges)} 个范围引用（应使用独立编号）: {ranges[:3]}")

    if unused:
        warnings.append(f"{len(unused)} 个来源未在报告中被引用")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "cited_sources": len(cited_indices),
        "total_sources": len(sources),
        "unused_sources": len(unused),
        "warnings": warnings,
    }
