"""
Text utilities: tokenization, similarity, keyword extraction.
Pure stdlib — no external dependencies.
"""

import math
import re
from collections import Counter

# --- Chinese/English stopwords ---

_EN_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could about above after again against all am and "
    "any at below between both but by down during each few for from further get "
    "got had has have he her here hers herself him himself his how i if in into "
    "is it its itself just me more most my myself no nor not now of off on once "
    "only or other our ours ourselves out over own s same she so some such t "
    "than that the their theirs them themselves then there these they this those "
    "through to too under until up very we were what when where which while who "
    "whom why with you your yours yourself yourselves".split()
)

_ZH_STOPWORDS = frozenset(
    "的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 "
    "看 好 自己 这 他 她 它 们 那 里 后 与 及 其 但 而 或 对 被 从 把 能 让 向 "
    "之 以 所 为 于 用 可 已 而且 然后 如果 因为 所以 但是 虽然 不过 还是 只是 "
    "这个 那个 什么 怎么 哪 多 少 大 小 中 更 最 该".split()
)

ALL_STOPWORDS = _EN_STOPWORDS | _ZH_STOPWORDS

# --- Tokenization ---

_EN_WORD_RE = re.compile(r"[a-zA-Z]{2,}")
_ZH_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """Split text into tokens (English words + individual CJK characters), lowercased."""
    tokens = []
    for m in _EN_WORD_RE.finditer(text):
        tokens.append(m.group().lower())
    for m in _ZH_CHAR_RE.finditer(text):
        tokens.append(m.group())
    return tokens


def tokenize_filtered(text: str) -> list[str]:
    """Tokenize and remove stopwords."""
    return [t for t in tokenize(text) if t not in ALL_STOPWORDS]


# --- Bag-of-Words cosine similarity ---


def bow_cosine(text_a: str, text_b: str) -> float:
    """Bag-of-words cosine similarity (for query dedup)."""
    tokens_a = tokenize_filtered(text_a)
    tokens_b = tokenize_filtered(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    ca = Counter(tokens_a)
    cb = Counter(tokens_b)
    common = set(ca) & set(cb)
    dot = sum(ca[k] * cb[k] for k in common)
    mag_a = math.sqrt(sum(v * v for v in ca.values()))
    mag_b = math.sqrt(sum(v * v for v in cb.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# --- TF-IDF cosine similarity ---


def _build_tfidf(docs: list[list[str]]) -> list[dict[str, float]]:
    """Build TF-IDF vectors for a list of tokenized documents."""
    n = len(docs)
    if n == 0:
        return []
    # document frequency
    df: dict[str, int] = Counter()
    for doc in docs:
        df.update(set(doc))
    # TF-IDF per doc
    vectors = []
    for doc in docs:
        tf = Counter(doc)
        total = len(doc) if doc else 1
        vec = {}
        for term, count in tf.items():
            idf = math.log((n + 1) / (df.get(term, 0) + 1)) + 1
            vec[term] = (count / total) * idf
        vectors.append(vec)
    return vectors


def tfidf_cosine(text_a: str, text_b: str) -> float:
    """TF-IDF cosine similarity between two texts (for learning dedup)."""
    tokens_a = tokenize_filtered(text_a)
    tokens_b = tokenize_filtered(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    vecs = _build_tfidf([tokens_a, tokens_b])
    va, vb = vecs[0], vecs[1]
    common = set(va) & set(vb)
    dot = sum(va[k] * vb[k] for k in common)
    mag_a = math.sqrt(sum(v * v for v in va.values()))
    mag_b = math.sqrt(sum(v * v for v in vb.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def tfidf_cosine_matrix(texts: list[str]) -> list[list[float]]:
    """Compute pairwise TF-IDF cosine similarity matrix."""
    n = len(texts)
    if n == 0:
        return []
    tokenized = [tokenize_filtered(t) for t in texts]
    vecs = _build_tfidf(tokenized)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            va, vb = vecs[i], vecs[j]
            common = set(va) & set(vb)
            if not common:
                continue
            dot = sum(va[k] * vb[k] for k in common)
            mag_a = math.sqrt(sum(v * v for v in va.values()))
            mag_b = math.sqrt(sum(v * v for v in vb.values()))
            if mag_a > 0 and mag_b > 0:
                sim = dot / (mag_a * mag_b)
                matrix[i][j] = sim
                matrix[j][i] = sim
    return matrix


# --- Keyword extraction ---


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Extract top-N keywords by TF (simple single-doc keyword extraction)."""
    tokens = tokenize_filtered(text)
    if not tokens:
        return []
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(top_n)]


def extract_keywords_batch(texts: list[str], top_n: int = 10) -> list[list[str]]:
    """Extract keywords for each text, using corpus-wide IDF weighting."""
    if not texts:
        return []
    tokenized = [tokenize_filtered(t) for t in texts]
    vecs = _build_tfidf(tokenized)
    results = []
    for vec in vecs:
        sorted_terms = sorted(vec.items(), key=lambda x: x[1], reverse=True)
        results.append([term for term, _ in sorted_terms[:top_n]])
    return results
