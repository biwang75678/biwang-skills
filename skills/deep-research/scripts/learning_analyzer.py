"""
Learning manager: dedup, clustering, conflict detection.
"""

import re
from collections import defaultdict

try:
    from . import text_utils
except ImportError:
    import text_utils  # type: ignore[no-redef]

DEDUP_THRESHOLD = 0.85
CLUSTER_THRESHOLD = 0.3  # keyword overlap for clustering
CONFLICT_SIM_THRESHOLD = 0.5

# Negation patterns for conflict detection
_NEGATION_PATTERNS = [
    re.compile(r"\b(not|no|never|neither|nor|isn't|aren't|wasn't|weren't|don't|doesn't|didn't|won't|wouldn't|can't|cannot|shouldn't|couldn't)\b", re.IGNORECASE),
    re.compile(r"\b(however|but|contrary|opposite|disagree|incorrect|false|wrong|myth|misconception|debunk)\b", re.IGNORECASE),
    re.compile(r"(不是|没有|不会|不能|并非|相反|错误|误解|否认|反驳|反对)", re.IGNORECASE),
]


def _has_negation(text: str) -> bool:
    return any(p.search(text) for p in _NEGATION_PATTERNS)


def deduplicate(learnings: list[dict]) -> list[dict]:
    """Mark duplicate learnings using TF-IDF cosine similarity."""
    texts = [l["text"] for l in learnings]
    n = len(texts)
    if n <= 1:
        return learnings

    sim_matrix = text_utils.tfidf_cosine_matrix(texts)

    # Mark later entries as duplicates of earlier ones
    for i in range(n):
        if learnings[i].get("is_duplicate"):
            continue
        for j in range(i + 1, n):
            if learnings[j].get("is_duplicate"):
                continue
            if sim_matrix[i][j] >= DEDUP_THRESHOLD:
                learnings[j]["is_duplicate"] = True
                learnings[j]["duplicate_of"] = learnings[i]["id"]

    return learnings


def cluster(learnings: list[dict]) -> dict:
    """Cluster learnings by keyword co-occurrence (connected components)."""
    active = [l for l in learnings if not l.get("is_duplicate")]
    if not active:
        return {"clusters": [], "noise": []}

    # Extract keywords for each learning
    texts = [l["text"] for l in active]
    keywords_list = text_utils.extract_keywords_batch(texts, top_n=8)

    # Assign keywords back
    for i, l in enumerate(active):
        l["topics"] = keywords_list[i]

    # Build adjacency via keyword overlap
    n = len(active)
    adj: dict[int, set[int]] = defaultdict(set)
    for i in range(n):
        ki = set(keywords_list[i])
        for j in range(i + 1, n):
            kj = set(keywords_list[j])
            if not ki or not kj:
                continue
            overlap = len(ki & kj) / min(len(ki), len(kj))
            if overlap >= CLUSTER_THRESHOLD:
                adj[i].add(j)
                adj[j].add(i)

    # Connected components via BFS
    visited = set()
    clusters: list[dict] = []
    cluster_id = 0

    for start in range(n):
        if start in visited:
            continue
        component = []
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            queue.extend(adj[node] - visited)

        if len(component) >= 1:
            # Determine cluster label from most common keywords
            all_kw: list[str] = []
            for idx in component:
                all_kw.extend(keywords_list[idx])
            kw_counts = {}
            for kw in all_kw:
                kw_counts[kw] = kw_counts.get(kw, 0) + 1
            top_kw = sorted(kw_counts, key=lambda k: kw_counts[k], reverse=True)[:5]

            cluster_info = {
                "cluster_id": cluster_id,
                "label": " / ".join(top_kw[:3]),
                "keywords": top_kw,
                "learning_ids": [active[idx]["id"] for idx in component],
                "size": len(component),
            }
            clusters.append(cluster_info)

            for idx in component:
                active[idx]["cluster_id"] = cluster_id

            cluster_id += 1

    return {
        "clusters": clusters,
        "total_clusters": len(clusters),
        "total_active_learnings": len(active),
    }


def detect_conflicts(learnings: list[dict]) -> list[dict]:
    """Detect conflicting learnings: similar topic + negation patterns."""
    active = [l for l in learnings if not l.get("is_duplicate")]
    if len(active) < 2:
        return []

    texts = [l["text"] for l in active]
    sim_matrix = text_utils.tfidf_cosine_matrix(texts)

    conflicts = []
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            if sim_matrix[i][j] < CONFLICT_SIM_THRESHOLD:
                continue
            # Check if one has negation and other doesn't, or both have different negation
            neg_i = _has_negation(texts[i])
            neg_j = _has_negation(texts[j])
            if neg_i != neg_j:
                conflict = {
                    "learning_a": active[i]["id"],
                    "text_a": texts[i][:200],
                    "learning_b": active[j]["id"],
                    "text_b": texts[j][:200],
                    "similarity": round(sim_matrix[i][j], 3),
                }
                conflicts.append(conflict)
                # Mark on learnings
                if active[j]["id"] not in active[i].get("conflicts_with", []):
                    active[i].setdefault("conflicts_with", []).append(active[j]["id"])
                if active[i]["id"] not in active[j].get("conflicts_with", []):
                    active[j].setdefault("conflicts_with", []).append(active[i]["id"])

    return conflicts


def analyze(learnings: list[dict]) -> dict:
    """Full analysis: dedup + cluster + conflict detection."""
    learnings = deduplicate(learnings)
    cluster_result = cluster(learnings)
    conflicts = detect_conflicts(learnings)

    duplicates = [l for l in learnings if l.get("is_duplicate")]

    return {
        "total_learnings": len(learnings),
        "active_learnings": len(learnings) - len(duplicates),
        "duplicates_found": len(duplicates),
        "clusters": cluster_result["clusters"],
        "total_clusters": cluster_result.get("total_clusters", 0),
        "conflicts": conflicts,
        "total_conflicts": len(conflicts),
    }
