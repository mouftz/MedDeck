import urllib.request
import json

ANKI_CONNECT_URL = "http://127.0.0.1:8765"

def _invoke(action: str, **params):
    request_data = {
        "action": action,
        "version": 6,
        "params": params
    }
    req = urllib.request.Request(
        ANKI_CONNECT_URL,
        data=json.dumps(request_data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    response = json.loads(urllib.request.urlopen(req).read().decode())
    if response.get("error"):
        raise Exception(f"AnkiConnect error: {response['error']}")
    return response["result"]

def get_deck_names():
    return _invoke("deckNames")

def create_deck(deck_name: str):
    return _invoke("createDeck", deck=deck_name)

def get_deck_fronts(deck_name: str) -> list:
    """Return the Front field of every existing note in a deck (for dedup)."""
    note_ids = _invoke("findNotes", query=f'deck:"{deck_name}"')
    if not note_ids:
        return []
    infos = _invoke("notesInfo", notes=note_ids)
    return [i["fields"]["Front"]["value"] for i in infos if "Front" in i.get("fields", {})]

def add_card(deck_name: str, front: str, back: str, tags: list = None):
    if tags is None:
        tags = []
    
    note = {
        "deckName": deck_name,
        "modelName": "Basic",
        "fields": {
            "Front": front,
            "Back": back
        },
        "options": {
            "allowDuplicate": False
        },
        "tags": tags
    }
    
    return _invoke("addNote", note=note)