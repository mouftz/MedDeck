"""Card generation pipeline: caching, dedup marking, and batch processing."""
from services import cache, dedup
from services.vision import generate_anki_card

DUP_THRESHOLD = 0.72


def generate_cached(image_base64: str) -> dict:
    """Generate a card, reusing a cached result for an identical screenshot."""
    hit = cache.get(image_base64)
    if hit is not None:
        return hit
    card = generate_anki_card(image_base64)
    cache.put(image_base64, card)
    return card


def mark_duplicate(card: dict, existing_fronts: list) -> dict:
    """Flag a generated card as a near-duplicate of an existing deck card."""
    front = card.get("anki_front", "")
    card["is_duplicate"] = bool(
        card.get("is_question") and dedup.is_duplicate(front, existing_fronts, DUP_THRESHOLD)
    )
    return card


def process_batch(images: list, existing_fronts: list) -> list:
    """Process many screenshots; each item is isolated so one failure never
    sinks the rest. Returns a per-item result with status."""
    results = []
    for i, image_base64 in enumerate(images):
        try:
            card = mark_duplicate(generate_cached(image_base64), existing_fronts)
            if not card.get("is_question"):
                status = "rejected"
            elif card.get("is_duplicate"):
                status = "duplicate"
            else:
                status = "ok"
            results.append({"index": i, "status": status, "card": card})
        except Exception as e:
            results.append({"index": i, "status": "failed", "error": str(e)})
    return results
