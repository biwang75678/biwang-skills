"""
Domain reputation database.
Maps domains to credibility levels: HIGH, MEDIUM, LOW.
"""

from urllib.parse import urlparse

# Credibility levels
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"

# --- Exact domain rules ---

_EXACT_RULES: dict[str, str] = {
    # Academic / Research
    "arxiv.org": HIGH,
    "scholar.google.com": HIGH,
    "pubmed.ncbi.nlm.nih.gov": HIGH,
    "ncbi.nlm.nih.gov": HIGH,
    "jstor.org": HIGH,
    "nature.com": HIGH,
    "science.org": HIGH,
    "sciencedirect.com": HIGH,
    "springer.com": HIGH,
    "link.springer.com": HIGH,
    "ieee.org": HIGH,
    "ieeexplore.ieee.org": HIGH,
    "acm.org": HIGH,
    "dl.acm.org": HIGH,
    "researchgate.net": HIGH,
    "semanticscholar.org": HIGH,
    "biorxiv.org": HIGH,
    "medrxiv.org": HIGH,
    "ssrn.com": HIGH,
    "plos.org": HIGH,
    "journals.plos.org": HIGH,
    "wiley.com": HIGH,
    "onlinelibrary.wiley.com": HIGH,
    "cell.com": HIGH,
    "thelancet.com": HIGH,
    "bmj.com": HIGH,
    "nejm.org": HIGH,
    "pnas.org": HIGH,
    "acs.org": HIGH,
    "rsc.org": HIGH,
    "frontiersin.org": HIGH,
    "mdpi.com": HIGH,
    "cambridge.org": HIGH,
    "academic.oup.com": HIGH,
    "doi.org": HIGH,
    "worldcat.org": HIGH,
    "cnki.net": HIGH,
    "wanfangdata.com.cn": HIGH,
    "cqvip.com": HIGH,
    "baidu.com": MEDIUM,
    # Government
    "who.int": HIGH,
    "un.org": HIGH,
    "worldbank.org": HIGH,
    "imf.org": HIGH,
    "europa.eu": HIGH,
    "data.gov": HIGH,
    "nih.gov": HIGH,
    "cdc.gov": HIGH,
    "fda.gov": HIGH,
    "epa.gov": HIGH,
    "nasa.gov": HIGH,
    "nist.gov": HIGH,
    "whitehouse.gov": HIGH,
    "congress.gov": HIGH,
    "supremecourt.gov": HIGH,
    "stats.gov.cn": HIGH,
    "mof.gov.cn": HIGH,
    "ndrc.gov.cn": HIGH,
    "miit.gov.cn": HIGH,
    "most.gov.cn": HIGH,
    "moe.gov.cn": HIGH,
    "cas.cn": HIGH,
    "nsfc.gov.cn": HIGH,
    # Major news / media
    "reuters.com": HIGH,
    "apnews.com": HIGH,
    "bbc.com": HIGH,
    "bbc.co.uk": HIGH,
    "nytimes.com": HIGH,
    "washingtonpost.com": HIGH,
    "theguardian.com": HIGH,
    "economist.com": HIGH,
    "ft.com": HIGH,
    "bloomberg.com": HIGH,
    "wsj.com": HIGH,
    "npr.org": HIGH,
    "pbs.org": HIGH,
    "aljazeera.com": HIGH,
    "xinhuanet.com": HIGH,
    "people.com.cn": HIGH,
    "chinadaily.com.cn": HIGH,
    "caixin.com": HIGH,
    "yicai.com": HIGH,
    "thepaper.cn": HIGH,
    # Tech media
    "techcrunch.com": MEDIUM,
    "wired.com": MEDIUM,
    "arstechnica.com": MEDIUM,
    "theverge.com": MEDIUM,
    "zdnet.com": MEDIUM,
    "cnet.com": MEDIUM,
    "engadget.com": MEDIUM,
    "venturebeat.com": MEDIUM,
    "36kr.com": MEDIUM,
    "infoq.cn": MEDIUM,
    "infoq.com": MEDIUM,
    "huxiu.com": MEDIUM,
    "jiqizhixin.com": MEDIUM,
    "leiphone.com": MEDIUM,
    # Reference / encyclopedia
    "en.wikipedia.org": MEDIUM,
    "zh.wikipedia.org": MEDIUM,
    "wikipedia.org": MEDIUM,
    "britannica.com": HIGH,
    "baike.baidu.com": MEDIUM,
    "zhihu.com": MEDIUM,
    # Tech documentation
    "docs.python.org": HIGH,
    "docs.oracle.com": HIGH,
    "developer.mozilla.org": HIGH,
    "learn.microsoft.com": HIGH,
    "cloud.google.com": HIGH,
    "docs.aws.amazon.com": HIGH,
    "kubernetes.io": HIGH,
    "docs.docker.com": HIGH,
    "go.dev": HIGH,
    "rust-lang.org": HIGH,
    "doc.rust-lang.org": HIGH,
    "typescriptlang.org": HIGH,
    "reactjs.org": HIGH,
    "react.dev": HIGH,
    "vuejs.org": HIGH,
    "angular.io": HIGH,
    "nodejs.org": HIGH,
    "docs.github.com": HIGH,
    # Developer communities
    "github.com": MEDIUM,
    "gitlab.com": MEDIUM,
    "stackoverflow.com": MEDIUM,
    "stackexchange.com": MEDIUM,
    "dev.to": MEDIUM,
    "medium.com": MEDIUM,
    "hackernews.com": MEDIUM,
    "news.ycombinator.com": MEDIUM,
    "lobste.rs": MEDIUM,
    "reddit.com": MEDIUM,
    "segmentfault.com": MEDIUM,
    "juejin.cn": MEDIUM,
    "csdn.net": MEDIUM,
    "cnblogs.com": MEDIUM,
    "oschina.net": MEDIUM,
    "v2ex.com": MEDIUM,
    # Low quality
    "pinterest.com": LOW,
    "quora.com": LOW,
    "answers.yahoo.com": LOW,
    "wikihow.com": LOW,
    "ehow.com": LOW,
    "about.com": LOW,
    "buzzfeed.com": LOW,
    "dailymail.co.uk": LOW,
    "mirror.co.uk": LOW,
    "thesun.co.uk": LOW,
    "nypost.com": LOW,
    "foxnews.com": LOW,
    "breitbart.com": LOW,
    "infowars.com": LOW,
    "rt.com": LOW,
    "sputniknews.com": LOW,
    "baijiahao.baidu.com": LOW,
    "sohu.com": LOW,
    "163.com": LOW,
    "toutiao.com": LOW,
    "kuaishou.com": LOW,
    "douyin.com": LOW,
    "weibo.com": LOW,
    "tieba.baidu.com": LOW,
    "zhidao.baidu.com": LOW,
    "wenku.baidu.com": LOW,
}

# --- Wildcard suffix rules ---

_SUFFIX_RULES: list[tuple[str, str]] = [
    (".edu", HIGH),
    (".edu.cn", HIGH),
    (".ac.uk", HIGH),
    (".ac.jp", HIGH),
    (".ac.kr", HIGH),
    (".gov", HIGH),
    (".gov.cn", HIGH),
    (".gov.uk", HIGH),
    (".go.jp", HIGH),
    (".mil", HIGH),
    (".int", HIGH),
    (".org", MEDIUM),  # generic .org gets MEDIUM
]


def get_credibility(url: str) -> str:
    """Return credibility level for a URL: HIGH, MEDIUM, or LOW."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().strip(".")
    except Exception:
        return MEDIUM

    if not host:
        return MEDIUM

    # Check exact match (try full host, then progressively strip subdomains)
    parts = host.split(".")
    for i in range(len(parts)):
        candidate = ".".join(parts[i:])
        if candidate in _EXACT_RULES:
            return _EXACT_RULES[candidate]

    # Check suffix rules (longest suffix first)
    sorted_suffixes = sorted(_SUFFIX_RULES, key=lambda x: len(x[0]), reverse=True)
    for suffix, level in sorted_suffixes:
        if host.endswith(suffix):
            return level

    return MEDIUM


def get_credibility_label(level: str) -> str:
    """Human-readable label for credibility level."""
    labels = {
        HIGH: "高可信度",
        MEDIUM: "中等可信度",
        LOW: "低可信度",
    }
    return labels.get(level, "未知")
