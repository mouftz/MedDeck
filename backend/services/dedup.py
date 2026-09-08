"""Near-duplicate detection via embedding cosine similarity.

The embedder is a pluggable seam: swap `embed` for a real embeddings API for
production quality. The offline char-n-gram embedder here needs no key.
"""
import math
import re
from collections import Counter

_WORD = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    return " ".join(_WORD.findall(text.lower()))


def embed(text: str, n: int = 3) -> Counter:
    s = _normalize(text)
    grams = Counter(s[i:i + n] for i in range(max(len(s) - n + 1, 0)))
    norm = math.sqrt(sum(v * v for v in grams.values())) or 1.0
    return Counter({g: v / norm for g, v in grams.items()})


def cosine(a: Counter, b: Counter) -> float:
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    return sum(w * large.get(g, 0.0) for g, w in small.items())


def max_similarity(new_text: str, existing_texts: list) -> float:
    if not existing_texts:
        return 0.0
    q = embed(new_text)
    return max(cosine(q, embed(t)) for t in existing_texts)


def is_duplicate(new_text: str, existing_texts: list, threshold: float = 0.72) -> bool:
    return max_similarity(new_text, existing_texts) >= threshold
