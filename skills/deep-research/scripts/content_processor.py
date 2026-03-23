"""
Content processor: HTML/Markdown content cleaning and extraction.
Uses only stdlib html.parser.
"""

import re
from html.parser import HTMLParser


# --- HTML Content Extractor ---

_SKIP_TAGS = frozenset({
    "script", "style", "nav", "footer", "header", "aside",
    "noscript", "iframe", "svg", "form", "button", "input",
    "select", "textarea", "meta", "link", "head",
})

_BLOCK_TAGS = frozenset({
    "p", "div", "section", "article", "main", "h1", "h2", "h3",
    "h4", "h5", "h6", "li", "tr", "blockquote", "pre", "table",
    "ul", "ol", "dl", "dt", "dd", "figcaption", "details", "summary",
})


class _ContentExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0
        self._tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in _SKIP_TAGS or self._skip_depth > 0:
            self._skip_depth += 1
            return
        self._tag_stack.append(tag)
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self.parts.append(text + " ")

    def get_text(self) -> str:
        raw = "".join(self.parts)
        # Collapse whitespace
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def extract_from_html(html_content: str) -> str:
    """Extract clean text from HTML."""
    parser = _ContentExtractor()
    try:
        parser.feed(html_content)
    except Exception:
        # If HTML parsing fails, try regex fallback
        text = re.sub(r"<[^>]+>", " ", html_content)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    return parser.get_text()


# --- Markdown cleaning ---

def clean_markdown(md_content: str) -> str:
    """Clean up Markdown content from WebFetch output."""
    lines = md_content.split("\n")
    cleaned = []
    skip_patterns = [
        re.compile(r"^\s*\[?\s*(Skip to|Jump to|Navigation|Menu|Sign in|Log in|Subscribe)", re.IGNORECASE),
        re.compile(r"^\s*Cookie", re.IGNORECASE),
        re.compile(r"^\s*(Share|Tweet|Pin|Email|Print)\s*$", re.IGNORECASE),
        re.compile(r"^\s*Advertisement\s*$", re.IGNORECASE),
    ]
    for line in lines:
        if any(p.match(line) for p in skip_patterns):
            continue
        cleaned.append(line)
    result = "\n".join(cleaned)
    # Collapse excessive blank lines
    result = re.sub(r"\n{4,}", "\n\n\n", result)
    return result.strip()


# --- Content type detection ---

_CONTENT_PATTERNS = {
    "paper": [
        re.compile(r"\b(abstract|introduction|methodology|conclusion|references|bibliography)\b", re.IGNORECASE),
        re.compile(r"\b(doi|arxiv|isbn|issn)\b", re.IGNORECASE),
        re.compile(r"\bet\s+al\b", re.IGNORECASE),
    ],
    "documentation": [
        re.compile(r"\b(api|sdk|install|configuration|usage|parameters|returns?|example)\b", re.IGNORECASE),
        re.compile(r"```"),
        re.compile(r"\b(deprecated|version|changelog)\b", re.IGNORECASE),
    ],
    "forum": [
        re.compile(r"\b(answered?|reply|replies|vote|upvote|comment|posted|asked)\b", re.IGNORECASE),
        re.compile(r"\b(ago|views?|reputation|badge)\b", re.IGNORECASE),
    ],
    "article": [
        re.compile(r"\b(published|author|editor|journalist|reporter)\b", re.IGNORECASE),
        re.compile(r"\b(opinion|editorial|column|feature|analysis)\b", re.IGNORECASE),
    ],
}


def detect_content_type(text: str) -> str:
    """Detect content type: paper, documentation, forum, article, or unknown."""
    scores: dict[str, int] = {}
    for ctype, patterns in _CONTENT_PATTERNS.items():
        score = sum(1 for p in patterns if p.search(text[:3000]))
        scores[ctype] = score
    if not scores:
        return "unknown"
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] >= 2 else "unknown"


def process_content(content: str, url: str = "") -> dict:
    """Process content: detect if HTML or Markdown, clean, detect type, truncate."""
    # Detect HTML
    is_html = bool(re.search(r"<\s*(html|body|div|p|span|head)\b", content[:500], re.IGNORECASE))

    if is_html:
        text = extract_from_html(content)
    else:
        text = clean_markdown(content)

    content_type = detect_content_type(text)

    # Truncate to reasonable size for LLM processing
    max_chars = 50000
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars] + "\n\n[... content truncated ...]"

    return {
        "text": text,
        "content_type": content_type,
        "char_count": len(text),
        "truncated": truncated,
        "source_url": url,
        "is_html_source": is_html,
    }
