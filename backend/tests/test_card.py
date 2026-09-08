import os

os.environ["MEDDECK_FAKE_VISION"] = "1"

import base64

import pytest
from fastapi.testclient import TestClient

from main import app
from routes import card as card_route
from services import cache, vision
from services.dedup import max_similarity

client = TestClient(app)


def _img(seed: str) -> str:
    return base64.b64encode(f"screenshot-{seed}".encode()).decode()


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    cache.reset()
    vision.vision_calls = 0
    # default: no existing cards, so nothing is a duplicate and no AnkiConnect needed
    monkeypatch.setattr(card_route, "get_deck_fronts", lambda deck: [])
    yield


def test_generate_card_returns_card():
    r = client.post("/generate-card", json={"image_base64": _img("a")})
    assert r.status_code == 200
    body = r.json()
    assert body["is_question"] is True
    assert body["anki_front"] and body["anki_back"]
    assert body["is_duplicate"] is False


def test_identical_screenshot_hits_cache():
    client.post("/generate-card", json={"image_base64": _img("same")})
    client.post("/generate-card", json={"image_base64": _img("same")})
    assert vision.vision_calls == 1
    assert cache.stats()["hits"] == 1


def test_distinct_screenshots_each_call_vision():
    client.post("/generate-card", json={"image_base64": _img("x")})
    client.post("/generate-card", json={"image_base64": _img("y")})
    assert vision.vision_calls == 2


def test_duplicate_is_flagged(monkeypatch):
    first = client.post("/generate-card", json={"image_base64": _img("dup")}).json()
    front = first["anki_front"]
    monkeypatch.setattr(card_route, "get_deck_fronts", lambda deck: [front])
    again = client.post("/generate-card", json={"image_base64": _img("dup")}).json()
    assert again["is_duplicate"] is True


def test_batch_processes_all_items():
    imgs = [_img(str(i)) for i in range(20)]
    r = client.post("/generate-batch", json={"images": imgs})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 20
    assert all(res["status"] in {"ok", "duplicate", "rejected", "failed"} for res in results)


def test_batch_isolates_a_single_failure(monkeypatch):
    from services import pipeline

    real = vision.generate_anki_card

    def flaky(image_base64):
        if image_base64 == _img("bad"):
            raise Exception("forced failure")
        return real(image_base64)

    monkeypatch.setattr(pipeline, "generate_anki_card", flaky)
    imgs = [_img("ok1"), _img("bad"), _img("ok2")]
    results = client.post("/generate-batch", json={"images": imgs}).json()["results"]
    statuses = [r["status"] for r in results]
    assert statuses.count("failed") == 1
    assert len(statuses) == 3
    assert any(r.get("error") for r in results)


def test_batch_dedups_against_existing(monkeypatch):
    one = client.post("/generate-batch", json={"images": [_img("q")]}).json()["results"][0]
    front = one["card"]["anki_front"]
    monkeypatch.setattr(card_route, "get_deck_fronts", lambda deck: [front])
    res = client.post("/generate-batch", json={"images": [_img("q")]}).json()["results"][0]
    assert res["status"] == "duplicate"


def test_dedup_similarity_orders_correctly():
    base = ["Most common cause of community-acquired pneumonia?"]
    near = max_similarity("Most common cause of community-acquired pneumonia?", base)
    far = max_similarity("What is the target INR for a mechanical valve?", base)
    assert near > far


def test_cache_returns_same_object():
    a = client.post("/generate-card", json={"image_base64": _img("k")}).json()
    b = client.post("/generate-card", json={"image_base64": _img("k")}).json()
    assert a["anki_front"] == b["anki_front"]


def test_empty_batch_returns_no_results():
    r = client.post("/generate-batch", json={"images": []})
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_root_health():
    assert client.get("/").json() == {"status": "ok"}
