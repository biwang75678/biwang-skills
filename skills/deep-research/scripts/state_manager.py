"""
State manager: JSON state persistence with atomic writes.
"""

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, urlencode
from uuid import uuid4

try:
    from . import text_utils
except ImportError:
    import text_utils  # type: ignore[no-redef]

STATE_FILE = ".deep-research-state.json"
QUERY_SIMILARITY_THRESHOLD = 0.75


def _default_state() -> dict:
    return {
        "version": 1,
        "config": {
            "query": "",
            "mode": "standard",
            "max_depth": 3,
            "base_breadth": 4,
            "report_type": "comprehensive",
        },
        "progress": {
            "current_depth": 0,
            "status": "initialized",
            "started_at": "",
            "updated_at": "",
        },
        "urls_visited": [],
        "queries_executed": [],
        "learnings": [],
        "followups": [],
        "analysis": None,
    }


def _normalize_url(url: str) -> str:
    """Normalize URL for dedup: lowercase scheme/host, strip trailing slash, sort query params."""
    try:
        p = urlparse(url)
        scheme = p.scheme.lower()
        host = (p.hostname or "").lower()
        port = f":{p.port}" if p.port and p.port not in (80, 443) else ""
        path = p.path.rstrip("/") or "/"
        # Sort query params
        params = parse_qs(p.query, keep_blank_values=True)
        sorted_query = urlencode(sorted(params.items()), doseq=True) if params else ""
        normalized = f"{scheme}://{host}{port}{path}"
        if sorted_query:
            normalized += f"?{sorted_query}"
        return normalized
    except Exception:
        return url.strip()


def _atomic_write(filepath: str, data):
    """Write JSON atomically using tempfile + os.replace with file locking."""
    dir_path = os.path.dirname(os.path.abspath(filepath))
    lock_path = filepath + ".lock"
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(lock_path, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            os.replace(tmp_path, filepath)
            fcntl.flock(lf, fcntl.LOCK_UN)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateManager:
    def __init__(self, state_dir: str = "."):
        self.filepath = os.path.join(state_dir, STATE_FILE)
        self._state: dict | None = None

    def _load(self) -> dict:
        if self._state is not None:
            return self._state
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                self._state = json.load(f)
                fcntl.flock(f, fcntl.LOCK_UN)
        else:
            self._state = _default_state()
        return self._state

    def _save(self):
        if self._state is not None:
            self._state["progress"]["updated_at"] = _now_iso()
            _atomic_write(self.filepath, self._state)

    @property
    def state(self) -> dict:
        return self._load()  # type: ignore[return-value]

    # --- Init ---

    def init(self, query: str, mode: str = "standard", max_depth: int = 3,
             base_breadth: int = 4, report_type: str = "comprehensive") -> dict:
        self._state = _default_state()
        self._state["config"].update({
            "query": query,
            "mode": mode,
            "max_depth": max_depth,
            "base_breadth": base_breadth,
            "report_type": report_type,
        })
        self._state["progress"]["started_at"] = _now_iso()
        self._state["progress"]["status"] = "initialized"
        self._save()
        return {"status": "ok", "state_file": self.filepath}

    # --- URL tracking ---

    def check_url(self, url: str) -> dict:
        normalized = _normalize_url(url)
        visited = {_normalize_url(u["url"]) for u in self.state["urls_visited"]}
        is_dup = normalized in visited
        return {"url": url, "normalized": normalized, "is_duplicate": is_dup}

    def add_url(self, url: str, title: str = "", content_type: str = "") -> dict:
        check = self.check_url(url)
        if check["is_duplicate"]:
            return {"status": "duplicate", "url": url}
        self.state["urls_visited"].append({
            "url": url,
            "normalized": check["normalized"],
            "title": title,
            "content_type": content_type,
            "visited_at": _now_iso(),
        })
        self._save()
        return {"status": "added", "url": url, "total_urls": len(self.state["urls_visited"])}

    # --- Query tracking ---

    def check_query(self, query: str) -> dict:
        executed = self.state["queries_executed"]
        for eq in executed:
            sim = text_utils.bow_cosine(query, eq["query"])
            if sim >= QUERY_SIMILARITY_THRESHOLD:
                return {
                    "query": query,
                    "is_duplicate": True,
                    "similar_to": eq["query"],
                    "similarity": round(sim, 3),
                }
        return {"query": query, "is_duplicate": False}

    def add_query(self, query: str, depth: int = 0) -> dict:
        check = self.check_query(query)
        if check["is_duplicate"]:
            return {"status": "duplicate", "query": query, "similar_to": check.get("similar_to")}
        self.state["queries_executed"].append({
            "query": query,
            "depth": depth,
            "executed_at": _now_iso(),
        })
        self._save()
        return {"status": "added", "query": query, "total_queries": len(self.state["queries_executed"])}

    # --- Learnings ---

    def add_learning(self, text: str, source_url: str = "", source_title: str = "",
                     depth: int = 0, query_origin: str = "",
                     credibility: str = "MEDIUM") -> dict:
        learning_id = str(uuid4())[:8]
        learning = {
            "id": learning_id,
            "text": text,
            "source_url": source_url,
            "source_title": source_title,
            "credibility": credibility,
            "depth_level": depth,
            "query_origin": query_origin,
            "topics": [],
            "is_duplicate": False,
            "cluster_id": None,
            "conflicts_with": [],
        }
        self.state["learnings"].append(learning)
        self._save()
        return {"status": "added", "id": learning_id,
                "total_learnings": len(self.state["learnings"])}

    # --- Follow-ups ---

    def add_followup(self, question: str, depth: int = 0, priority: str = "medium") -> dict:
        self.state["followups"].append({
            "question": question,
            "depth": depth,
            "priority": priority,
            "used": False,
        })
        self._save()
        return {"status": "added", "total_followups": len(self.state["followups"])}

    def get_unused_followups(self, limit: int = 10) -> list[dict]:
        unused = [f for f in self.state["followups"] if not f.get("used")]
        # Sort by priority
        prio_order = {"high": 0, "medium": 1, "low": 2}
        unused.sort(key=lambda x: prio_order.get(x.get("priority", "medium"), 1))
        return unused[:limit]

    def mark_followup_used(self, question: str) -> dict:
        for f in self.state["followups"]:
            if f["question"] == question:
                f["used"] = True
                self._save()
                return {"status": "marked", "question": question}
        return {"status": "not_found", "question": question}

    # --- Progress ---

    def set_status(self, status: str) -> dict:
        self.state["progress"]["status"] = status
        self._save()
        return {"status": status}

    def set_depth(self, depth: int) -> dict:
        self.state["progress"]["current_depth"] = depth
        self._save()
        return {"current_depth": depth}

    # --- Analysis ---

    def set_analysis(self, analysis: dict) -> dict:
        self.state["analysis"] = analysis
        self._save()
        return {"status": "ok"}

    # --- Stats ---

    def get_stats(self) -> dict:
        s = self.state
        return {
            "config": s["config"],
            "progress": s["progress"],
            "total_urls": len(s["urls_visited"]),
            "total_queries": len(s["queries_executed"]),
            "total_learnings": len(s["learnings"]),
            "total_followups": len(s["followups"]),
            "unused_followups": len([f for f in s["followups"] if not f.get("used")]),
            "has_analysis": s["analysis"] is not None,
        }

    # --- Sources.json persistence ---

    def save_sources_json(self, sources: list) -> dict:
        """Persist sources list to standalone sources.json for progressive assembly."""
        path = os.path.join(os.path.dirname(self.filepath), "sources.json")
        _atomic_write(path, sources)
        return {"status": "ok", "path": path, "total_sources": len(sources)}

    def load_sources_json(self) -> list:
        """Load sources from standalone sources.json."""
        path = os.path.join(os.path.dirname(self.filepath), "sources.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
