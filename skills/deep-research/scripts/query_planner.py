"""
Query planner: depth/breadth control, termination decisions, mode configs.
"""

# --- Mode configurations ---

MODE_CONFIGS = {
    "quick": {
        "max_depth": 1,
        "base_breadth": 3,
        "phases": ["SCOPE", "SEARCH", "SYNTHESIZE"],
        "min_sources": 5,
        "target_words": "2000-4000",
    },
    "standard": {
        "max_depth": 3,
        "base_breadth": 4,
        "phases": ["SCOPE", "PLAN", "SEARCH", "ANALYZE", "SYNTHESIZE"],
        "min_sources": 10,
        "target_words": "4000-8000",
    },
    "deep": {
        "max_depth": 5,
        "base_breadth": 5,
        "phases": ["SCOPE", "PLAN", "SEARCH", "ANALYZE", "CRITIQUE", "SYNTHESIZE", "VALIDATE"],
        "min_sources": 15,
        "target_words": "8000-15000",
    },
}


def get_mode_config(mode: str) -> dict:
    """Get configuration for a research mode."""
    return MODE_CONFIGS.get(mode, MODE_CONFIGS["standard"])


def suggest_queries(state: dict) -> dict:
    """Suggest how many queries and subagents to use for current depth."""
    mode = state["config"].get("mode", "standard")
    depth = state["progress"]["current_depth"]
    base = state["config"]["base_breadth"]
    breadth = compute_effective_breadth(base, depth)
    agents = max(1, breadth // 2)
    return {
        "mode": mode,
        "breadth": breadth,
        "agents": agents,
        "queries_per_agent": max(2, (breadth + agents - 1) // agents),
    }


def compute_effective_breadth(base_breadth: int, depth: int) -> int:
    """Compute breadth for a given depth level with exponential decay."""
    effective = max(2, int(base_breadth * (0.7 ** depth)))
    return effective


def should_continue(state: dict) -> dict:
    """Determine whether to continue researching.

    Returns decision with reasoning.
    """
    config = state["config"]
    progress = state["progress"]
    learnings = state["learnings"]
    followups = state["followups"]

    current_depth = progress["current_depth"]
    max_depth = config["max_depth"]
    base_breadth = config["base_breadth"]

    # Reason 1: Max depth reached
    if current_depth >= max_depth:
        return {
            "should_continue": False,
            "stop_reason": "max_depth_reached",
            "message": f"已达到最大搜索深度 {max_depth}",
            "current_depth": current_depth,
            "max_depth": max_depth,
        }

    # Reason 2: No follow-up questions available
    unused_followups = [f for f in followups if not f.get("used")]
    if current_depth > 0 and not unused_followups:
        return {
            "should_continue": False,
            "stop_reason": "no_followups",
            "message": "没有更多的后续问题可供探索",
            "current_depth": current_depth,
        }

    # Reason 3: Diminishing returns
    if current_depth > 0 and learnings:
        current_depth_learnings = [l for l in learnings if l.get("depth_level") == current_depth]
        prev_depth_learnings = [l for l in learnings if l.get("depth_level") == current_depth - 1]
        if prev_depth_learnings:
            ratio = len(current_depth_learnings) / max(1, len(prev_depth_learnings))
            if ratio < 0.20:
                return {
                    "should_continue": False,
                    "stop_reason": "diminishing_returns",
                    "message": f"当前层收获 ({len(current_depth_learnings)}) 不足上层 ({len(prev_depth_learnings)}) 的 20%，边际递减",
                    "current_depth": current_depth,
                    "ratio": round(ratio, 3),
                }

    # Reason 4: Saturation (all queries are duplicates)
    # This is implicitly handled by the query dedup in state_manager

    # Continue
    next_depth = current_depth + 1
    next_breadth = compute_effective_breadth(base_breadth, next_depth)

    return {
        "should_continue": True,
        "next_depth": next_depth,
        "next_breadth": next_breadth,
        "available_followups": len(unused_followups),
        "total_learnings": len(learnings),
        "current_depth": current_depth,
        "message": f"继续搜索: 深度 {next_depth}, 广度 {next_breadth}, 可用问题 {len(unused_followups)} 个",
    }
