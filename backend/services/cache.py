"""In-memory response cache keyed on the source image hash."""
import hashlib

_store = {}
_stats = {"hits": 0, "misses": 0}


def image_key(image_base64: str) -> str:
    return hashlib.sha256(image_base64.encode()).hexdigest()


def get(image_base64: str):
    key = image_key(image_base64)
    if key in _store:
        _stats["hits"] += 1
        return _store[key]
    _stats["misses"] += 1
    return None


def put(image_base64: str, value: dict) -> None:
    _store[image_key(image_base64)] = value


def stats() -> dict:
    total = _stats["hits"] + _stats["misses"]
    return {**_stats, "hit_rate": _stats["hits"] / total if total else 0.0}


def reset() -> None:
    _store.clear()
    _stats.update(hits=0, misses=0)
