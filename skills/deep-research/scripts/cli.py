#!/usr/bin/env python3
"""
Unified CLI for deep-research agent.
All output is JSON for agent parsing.
"""

import argparse
import json
import os
import sys

# Ensure package is importable when run directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Import sibling modules directly (works whether run as script or package)
import state_manager  # type: ignore[import-not-found]
import content_processor  # type: ignore[import-not-found]
import learning_analyzer  # type: ignore[import-not-found]
import query_planner  # type: ignore[import-not-found]
import report_generator  # type: ignore[import-not-found]
import domain_reputation  # type: ignore[import-not-found]


def _json_out(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _get_sm(args) -> state_manager.StateManager:
    state_dir = getattr(args, "state_dir", None) or "."
    return state_manager.StateManager(state_dir)


# --- Commands ---

def cmd_init(args):
    sm = _get_sm(args)
    mode_cfg = query_planner.get_mode_config(args.mode)
    result = sm.init(
        query=args.query,
        mode=args.mode,
        max_depth=args.depth or mode_cfg["max_depth"],
        base_breadth=args.breadth or mode_cfg["base_breadth"],
        report_type=args.report_type,
    )
    _json_out(result)


def cmd_state(args):
    sm = _get_sm(args)
    subcmd = args.state_cmd
    # --text flag overrides positional text
    text = args.text_flag if args.text_flag else args.text

    if subcmd == "check-query":
        _json_out(sm.check_query(text))
    elif subcmd == "check-url":
        _json_out(sm.check_url(text))
    elif subcmd == "add-query":
        _json_out(sm.add_query(text, depth=args.depth))
    elif subcmd == "add-url":
        _json_out(sm.add_url(text, title=args.title or ""))
    elif subcmd == "add-learning":
        cred = domain_reputation.get_credibility(args.url) if args.url else "MEDIUM"
        _json_out(sm.add_learning(
            text=text,
            source_url=args.url or "",
            source_title=args.title or "",
            depth=args.depth,
            query_origin=args.query_origin or "",
            credibility=cred,
        ))
    elif subcmd == "add-followup":
        _json_out(sm.add_followup(text, depth=args.depth, priority=args.priority))
    elif subcmd == "followups":
        _json_out(sm.get_unused_followups(limit=args.limit))
    elif subcmd == "mark-followup":
        _json_out(sm.mark_followup_used(text))
    elif subcmd == "set-status":
        _json_out(sm.set_status(text))
    elif subcmd == "set-depth":
        _json_out(sm.set_depth(int(text)))
    elif subcmd == "next-depth":
        _json_out(query_planner.should_continue(sm.state))
    elif subcmd == "stats":
        _json_out(sm.get_stats())
    elif subcmd == "dump":
        _json_out(sm.state)
    else:
        _json_out({"error": f"Unknown state subcommand: {subcmd}"})


def cmd_process_content(args):
    content = sys.stdin.read()
    result = content_processor.process_content(content, url=args.url or "")
    _json_out(result)


def cmd_analyze_learnings(args):
    sm = _get_sm(args)
    learnings = sm.state["learnings"]
    if not learnings:
        _json_out({"error": "No learnings to analyze"})
        return
    analysis = learning_analyzer.analyze(learnings)
    sm.set_analysis(analysis)
    _json_out(analysis)


def cmd_generate_report(args):
    sm = _get_sm(args)
    report_type = args.report_type if hasattr(args, "report_type") and args.report_type else ""
    report = report_generator.generate_report(sm.state, report_type=report_type)

    # Write report to file
    output_file = args.output or "research-report.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    _json_out({
        "status": "ok",
        "output_file": output_file,
        "report_type": report_type or sm.state["config"].get("report_type", "comprehensive"),
        "char_count": len(report),
    })


def cmd_validate_report(args):
    sm = _get_sm(args)
    report_path = args.report_file
    if not os.path.exists(report_path):
        _json_out({"error": f"Report file not found: {report_path}"})
        return
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    result = report_generator.validate_report(content, sm.state)
    _json_out(result)


def cmd_generate_section(args):
    sm = _get_sm(args)
    section = report_generator.generate_section(
        sm.state, section_type=args.section_type, section_index=args.index)
    _json_out({"status": "ok", "section_type": args.section_type, "content": section})


def cmd_sources(args):
    sm = _get_sm(args)
    result = report_generator.save_sources_json(sm.state, output_dir=args.state_dir or ".")
    _json_out(result)


def cmd_suggest_queries(args):
    sm = _get_sm(args)
    _json_out(query_planner.suggest_queries(sm.state))


def cmd_credibility(args):
    url = args.url
    level = domain_reputation.get_credibility(url)
    label = domain_reputation.get_credibility_label(level)
    _json_out({"url": url, "credibility": level, "label": label})


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        prog="deep-research",
        description="Deep research agent CLI toolkit",
    )
    parser.add_argument("--state-dir", default=".", help="Directory for state file")
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize research state")
    p_init.add_argument("--query", required=True, help="Research query")
    p_init.add_argument("--mode", default="standard", choices=["quick", "standard", "deep"],
                        help="Research mode")
    p_init.add_argument("--depth", type=int, default=0, help="Max search depth (0=auto from mode)")
    p_init.add_argument("--breadth", type=int, default=0, help="Base breadth (0=auto from mode)")
    p_init.add_argument("--report-type", default="comprehensive",
                        choices=["comprehensive", "brief", "outline"])

    # state
    p_state = sub.add_parser("state", help="State management subcommands")
    p_state.add_argument("state_cmd", choices=[
        "check-query", "check-url", "add-query", "add-url", "add-learning",
        "add-followup", "followups", "mark-followup",
        "set-status", "set-depth", "next-depth", "stats", "dump",
    ])
    p_state.add_argument("text", nargs="?", default="", help="Text argument (positional)")
    p_state.add_argument("--text", dest="text_flag", default="", help="Text argument (flag, overrides positional)")
    p_state.add_argument("--url", default="", help="Source URL")
    p_state.add_argument("--title", default="", help="Source title")
    p_state.add_argument("--depth", type=int, default=0, help="Depth level")
    p_state.add_argument("--query-origin", default="", help="Original query")
    p_state.add_argument("--priority", default="medium", choices=["high", "medium", "low"])
    p_state.add_argument("--limit", type=int, default=10, help="Limit for followups")

    # process-content
    p_content = sub.add_parser("process-content", help="Process content from stdin")
    p_content.add_argument("--url", default="", help="Source URL")

    # analyze-learnings
    sub.add_parser("analyze-learnings", help="Analyze all learnings")

    # generate-report
    p_report = sub.add_parser("generate-report", help="Generate research report")
    p_report.add_argument("--output", "-o", default="research-report.md", help="Output file")
    p_report.add_argument("--report-type", default="", choices=["comprehensive", "brief", "outline", ""])

    # validate-report
    p_validate = sub.add_parser("validate-report", help="Validate report citations")
    p_validate.add_argument("report_file", help="Path to report markdown file")

    # generate-section
    p_section = sub.add_parser("generate-section", help="Generate a single report section")
    p_section.add_argument("section_type", choices=[
        "header", "summary", "toc", "cluster", "conflicts", "sources", "methodology"])
    p_section.add_argument("--index", type=int, default=0, help="Section index (for cluster)")

    # sources
    sub.add_parser("sources", help="Save sources.json for progressive assembly")

    # suggest-queries
    sub.add_parser("suggest-queries", help="Suggest query count and subagent allocation")

    # credibility
    p_cred = sub.add_parser("credibility", help="Check URL credibility")
    p_cred.add_argument("url", help="URL to check")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "init": cmd_init,
        "state": cmd_state,
        "process-content": cmd_process_content,
        "analyze-learnings": cmd_analyze_learnings,
        "generate-report": cmd_generate_report,
        "generate-section": cmd_generate_section,
        "validate-report": cmd_validate_report,
        "sources": cmd_sources,
        "suggest-queries": cmd_suggest_queries,
        "credibility": cmd_credibility,
    }

    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
